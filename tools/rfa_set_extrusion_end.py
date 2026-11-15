#!/usr/bin/env python3
"""rfa_set_extrusion_end.py IN.rfa OUT.rfa EID NEW_END   (LAB TOOL, not wired into any product path)

Sets the EndOffset of a family Extrusion by patching the extrusion's Z item the way the Revit-made pairs showed (synthetic families, Revit 2024):
the end offset E sits as an unaligned double at Z body offsets 72 and 120, and every other changed slot holds E-StartOffset (31 slots at fixed offsets, same in a 2x2 and a 3x5 profile pair).
Each slot moves by the same delta. The Z stamp (Adler32) is rewritten and the partition is saved with the segment writer ('fit' layout).
Refuses (rc 2, nothing written) when the layout is not the one measured: slots at 72/120 disagree, fewer/more than 31 matching slots, multi-partition file, etc.
Evidence status: offline only (Z item byte-equal to Revit's own result); Revit VM readback pending."""
import sys, os, struct, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import segedit as SE
SLOTS = (72, 120, 837, 869, 1063, 1095, 1160, 1176, 1402, 1434, 1499, 1515, 1741, 1773, 1838, 1854, 1983, 1999, 2134, 2416, 2449, 2482, 2590, 2623, 2656, 2764, 2797, 2830, 2938, 2971, 3004)      # identical in both Revit-made pairs (2x2 and 3x5 profile)
NSLOTS = len(SLOTS)


def patch_body(body, new):
    """-> (new body, slot count); raises SE.Refused when the measured layout does not hold"""
    if len(body) != 3060: raise SE.Refused('Z item is %d bytes: the slot layout was measured only on the 3060-byte Z item of a 4-sided rectangle profile (Autodesk sample families have 6912..9650-byte ones)' % len(body))
    e0, e1 = struct.unpack_from('<d', body, 72)[0], struct.unpack_from('<d', body, 120)[0]
    if e0 != e1 or not (-1e4 < e0 < 1e4): raise SE.Refused('end offset slots 72/120 disagree (%r vs %r)' % (e0, e1))
    s = struct.unpack_from('<d', body, 837)[0]; start = e0 - s
    nb = bytearray(body); n = 0
    for st in SLOTS:
        if st + 8 > len(nb): raise SE.Refused('slot %d outside the Z item' % st)
        v = struct.unpack_from('<d', nb, st)[0]
        for old, nw in ((e0, new), (e0 - start, new - start)):
            if abs(v - old) < 1e-12: struct.pack_into('<d', nb, st, nw); n += 1; break
        else: raise SE.Refused('slot %d holds %r, expected %r or %r' % (st, v, e0, e0 - start))
    return bytes(nb), n


def patch_body_generic(body, new, start):
    """other profiles (hexagon 4254 B, 2-arc circle 4234 B, triangle 2463 B measured, 3 Revit-made pairs): the changed slots are exactly the unaligned doubles equal to E (end) or E-start.
    START comes from the R record. Value matching is only safe when those values cannot collide with profile coordinates: refuses when E or E-start is 0 or +-1, when slots 72/120 disagree, or when fewer than 8 slots match."""
    if not (2000 < len(body) < 12000): raise SE.Refused('Z item is %d bytes: outside the measured range 2463..4254' % len(body))
    e0, e1 = struct.unpack_from('<d', body, 72)[0], struct.unpack_from('<d', body, 120)[0]
    if e0 != e1 or not (-1e4 < e0 < 1e4): raise SE.Refused('end offset slots 72/120 disagree (%r vs %r)' % (e0, e1))
    d0 = e0 - start
    for v in (e0, d0, new, new - start):
        if abs(v) < 1e-9 or abs(abs(v) - 1.0) < 1e-9: raise SE.Refused('value %r is 0 or +-1: value matching would collide with unit constants' % v)
    nb = bytearray(body); n = 0
    for i in range(len(body) - 7):
        v = struct.unpack_from('<d', body, i)[0]
        if abs(v - e0) < 1e-12: struct.pack_into('<d', nb, i, new); n += 1
        elif abs(v - d0) < 1e-12: struct.pack_into('<d', nb, i, new - start); n += 1
    if n < 8: raise SE.Refused('only %d slots matched' % n)
    return bytes(nb), n


def main(a):
    src, dst, eid, new = a[0], a[1], int(a[2]), float(a[3])
    if not (-1e4 < new < 1e4): print('refused: new end offset %r is not a finite value within +-1e4 ft' % new); return 2
    if os.path.exists(dst): print('refused: output exists'); return 2
    try:
        s = SE.Session(src); T = s.template(eid); W = s.ctx.W
        if T['cls'] != 'ExtrusionElem': raise SE.Refused('element %d is %s, not ExtrusionElem' % (eid, T['cls']))
        zk = T['_zk']; L = struct.unpack('<I', s.J.get(zk + W + 4, 4))[0]; body = s.J.get(zk + W + 8, L)
        if zlib.adler32(body) & 0xffffffff != struct.unpack('<I', s.J.get(zk + W, 4))[0]: raise SE.Refused('Z stamp does not match its body')
        e0 = struct.unpack_from('<d', body, 72)[0]
        i, r, log, q = s.trace(eid)
        dbl = [l for l in log if l[1] == 'ParamValueDouble.m_value' and l[3] - l[2] == 8]
        if len(body) == 3060: nb, n = patch_body(body, new)
        else:
            ends = [k for k, l in enumerate(dbl) if abs(struct.unpack('<d', s.J.get(l[2], 8))[0] - e0) < 1e-12]
            if len(ends) != 1 or ends[0] + 1 >= len(dbl) or len(dbl) != 2: raise SE.Refused('R record does not hold exactly (end, start) ParamValueDouble pair')
            nb, n = patch_body_generic(body, new, struct.unpack('<d', s.J.get(dbl[ends[0] + 1][2], 8))[0])
        # (2) element header: exactly one unaligned double equal to the old end offset, no stamp in the header
        hdr = T['hdr']; hh = [o for o in range(len(hdr) - 7) if abs(struct.unpack_from('<d', hdr, o)[0] - e0) < 1e-12 and struct.unpack_from('<d', hdr, o)[0] != 0.0]
        if len(hh) != 1: raise SE.Refused('element header holds %d slots equal to the old end offset %r (expected exactly 1)' % (len(hh), e0))
        # (3) R record: exactly one ParamValueDouble.m_value equal to the old end offset (what the Revit API reads back)
        pv = [l for l in log if l[1] == 'ParamValueDouble.m_value' and l[3] - l[2] == 8 and abs(struct.unpack('<d', s.J.get(l[2], 8))[0] - e0) < 1e-12]
        if len(pv) != 1 or pv[0][3] - pv[0][2] != 8: raise SE.Refused('R record holds %d ParamValueDouble slots equal to the old end offset (expected exactly 1)' % len(pv))
        s._spans(zk + W + 8, body, nb, 'extrusion end')
        s._replace(zk + W, 4, struct.pack('<I', zlib.adler32(nb) & 0xffffffff), 'z stamp')
        s._replace(T['_hk'] + hh[0], 8, struct.pack('<d', new), 'header end offset')
        s._modify(i, q, r, [(pv[0][2], 8, struct.pack('<d', new))], 'R end offset')
        s.write(dst, mode='fit')
    except SE.Refused as e:
        print('refused:', e); return 2
    print('ok: %d Z slots + header + R value patched -> %s' % (n, dst)); return 0


if __name__ == '__main__': sys.exit(main(sys.argv[1:]) if len(sys.argv) == 5 else print(__doc__) or 2)
