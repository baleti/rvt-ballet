#!/usr/bin/env python3
"""rfa_set_extrusion_start.py IN.rfa OUT.rfa EID NEW_START   (LAB TOOL, not wired into any product path)

StartOffset edit of a family Extrusion, three places like the end offset (one Revit-made pair, synthetic 3x5 rectangle, Revit 2024, 3060-byte Z item):
Z item: exactly 3 unaligned doubles equal to the old start become the new start, exactly 24 equal to E-start become E-newstart; element header: exactly one double equal to the old start;
R record: the second ParamValueDouble (end, start) pair member. Refuses on any other count, non-2024 year, non-3060 Z, value collision outside the element (profile coordinates), bad values."""
import sys, os, struct, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import segedit as SE


def main(a):
    try: src, dst, eid, new = a[0], a[1], int(a[2]), float(a[3])
    except ValueError as e: print('refused: bad EID / NEW_START argument (%s)' % e); return 2
    if new != 0.0 and abs(new) < 1e-9: print('refused: new start offset %r is a denormal-scale value' % new); return 2
    if not (-1e4 < new < 1e4): print('refused: new start offset %r is not a finite value within +-1e4 ft' % new); return 2
    if os.path.exists(dst): print('refused: output exists'); return 2
    try:
        if str(SE.file_version(src)) != '2024': raise SE.Refused('Revit year: the layout was measured on Revit 2024 files only')
        s = SE.Session(src); T = s.template(eid); W = s.ctx.W
        if T['cls'] != 'ExtrusionElem': raise SE.Refused('element %d is %s, not ExtrusionElem' % (eid, T['cls']))
        zk = T['_zk']; L = struct.unpack('<I', s.J.get(zk + W + 4, 4))[0]; body = s.J.get(zk + W + 8, L)
        if zlib.adler32(body) & 0xffffffff != struct.unpack('<I', s.J.get(zk + W, 4))[0]: raise SE.Refused('Z stamp does not match its body')
        if len(body) != 3060: raise SE.Refused('Z item is %d bytes: measured on 3060 only' % len(body))
        i, r, log, q = s.trace(eid)
        dbl = [l for l in log if l[1] == 'ParamValueDouble.m_value' and l[3] - l[2] == 8]
        if len(dbl) != 2: raise SE.Refused('R record does not hold exactly an (end, start) ParamValueDouble pair')
        e0 = struct.unpack('<d', s.J.get(dbl[0][2], 8))[0]; st = struct.unpack('<d', s.J.get(dbl[1][2], 8))[0]
        if new >= e0 - 1e-9: raise SE.Refused('new start offset %r is not below the end offset %r (zero or negative depth)' % (new, e0))
        ez = struct.unpack_from('<d', body, 72)[0]
        if abs(ez - e0) > 1e-12: raise SE.Refused('Z end slot %r disagrees with the R record end %r' % (ez, e0))
        d0 = ez - st
        for v in (st, d0, new, ez - new):
            if abs(v) < 1e-9 or abs(abs(v) - 1.0) < 1e-9: raise SE.Refused('value %r is 0 or +-1: would collide with unit constants' % v)
        nb = bytearray(body); n0 = n1 = n2 = 0
        for k in range(len(body) - 7):
            v = struct.unpack_from('<d', body, k)[0]
            if abs(v - st) < 1e-12: struct.pack_into('<d', nb, k, new); n0 += 1
            elif abs(v - d0) < 1e-12: struct.pack_into('<d', nb, k, e0 - new); n1 += 1
            elif abs(v - ez) < 1e-12: struct.pack_into('<d', nb, k, e0); n2 += 1      # Revit re-stores the end as the exact R-record value (1 ulp from the old Z copy)
        if (n0, n1, n2) != (3, 24, 7): raise SE.Refused('slot counts (start, end-start, end) = (%d, %d, %d), measured (3, 24, 7)' % (n0, n1, n2))
        hdr = T['hdr']; hh = [o for o in range(len(hdr) - 7) if abs(struct.unpack_from('<d', hdr, o)[0] - st) < 1e-12]
        he = [o for o in range(len(hdr) - 7) if abs(struct.unpack_from('<d', hdr, o)[0] - ez) < 1e-12]
        if len(hh) != 1 or len(he) != 1: raise SE.Refused('element header holds %d slots equal to the old start (expected 1)' % len(hh))
        pats = [struct.pack('<d', st), struct.pack('<d', d0), struct.pack('<d', ez)]
        spans = [(zk, zk + W + 8 + L), (T['_hk'], T['_hk'] + len(hdr)), (i, q)]
        for pt, offs in SE.occurrences(s.sp, pats).items():
            out = [o for o in offs if not any(x <= o < y for x, y in spans)]
            if out: raise SE.Refused('the old start / end-start value also occurs %d time(s) outside this extrusion: value matching is ambiguous' % len(out))
        s._spans(zk + W + 8, body, bytes(nb), 'extrusion start')
        s._replace(zk + W, 4, struct.pack('<I', zlib.adler32(bytes(nb)) & 0xffffffff), 'z stamp')
        s._replace(T['_hk'] + hh[0], 8, struct.pack('<d', new), 'header start')
        s._replace(T['_hk'] + he[0], 8, struct.pack('<d', e0), 'header end')
        s._modify(i, q, r, [(dbl[1][2], 8, struct.pack('<d', new))], 'R start')
        s.write(dst, mode='fit')
    except SE.Refused as e:
        print('refused:', e); return 2
    except Exception as e:
        print('refused: input could not be read (%s: %s)' % (type(e).__name__, str(e)[:80])); return 2
    print('ok: start %r -> %r, %d + %d Z slots + header + R patched -> %s' % (st, new, n0, n1, dst)); return 0


if __name__ == '__main__': sys.exit(main(sys.argv[1:]) if len(sys.argv) == 5 else print(__doc__) or 2)
