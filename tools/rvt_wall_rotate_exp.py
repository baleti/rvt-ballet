#!/usr/bin/env python3
"""rvt_wall_rotate_exp.py SRC DST EID DEG [THICKNESS_FT]: EXPERIMENT (not wired into the save path, gate stays off). Rotates one ISOLATED straight wall about its location-line midpoint
by patching exactly the fields the Revit-made rotate (wrot4, Structural 2024) changes: GLine.m_origin/m_dirVec, Plane#1..#4 (origin, xVec; #2/#3 = origin +/- t*normal) and the header
outline box (AABB of the footprint corners, z base..top). The cached BRep in the zone item is NOT touched (unverified for rotate). Writes DST only; Autodesk samples / synthetic only."""
import os, sys, math, struct
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
import rvtedit
src, dst, eid, deg = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
if os.path.realpath(src) == os.path.realpath(dst): sys.exit('REFUSED: output equals input')
ed = rvtedit.Edit(src); tr = ed.g.e.trace(eid); body = ed.g.e.m.parts[tr[0]]['joined']
L = [l for l in tr[3] if l[3] - l[2] in (16, 24)]
dbl = lambda off, n: list(struct.unpack_from('<%dd' % n, body, off))
gl = [l for l in L if l[1] == 'GLine.m_origin']; gd = [l for l in L if l[1] == 'GLine.m_dirVec']
po = [l for l in L if l[1] == 'Plane.m_origin']; px = [l for l in L if l[1] == 'Plane.m_xVec']
if len(gl) != 1 or len(gd) != 1 or len(po) != 4 or len(px) != 4: sys.exit('REFUSED: not a plain straight wall record (GLine %d dir %d planes %d/%d)' % (len(gl), len(gd), len(po), len(px)))
ep = [l for l in tr[3] if l[1] == 'GCurve.m_endParams'][0]; s0, s1 = dbl(ep[2], 2)
o = dbl(gl[0][2], 3); d = dbl(gd[0][2], 3)
t = float(sys.argv[5]) if len(sys.argv) > 5 else math.dist(dbl(po[0][2], 3)[:2], dbl(po[1][2], 3)[:2])
if not (0.01 < t < 20): sys.exit('REFUSED: implausible half thickness %r' % t)
p0 = (o[0] + d[0] * s0, o[1] + d[1] * s0); p1 = (o[0] + d[0] * s1, o[1] + d[1] * s1); cx, cy = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
a = math.radians(deg); co, si = math.cos(a), math.sin(a)
R = lambda x, y: (co * x - si * y, si * x + co * y); P = lambda x, y: (lambda r: (cx + r[0], cy + r[1]))(R(x - cx, y - cy))
no = P(o[0], o[1]); nd = R(d[0], d[1]); n = (-nd[1], nd[0])
ed_ = []; pk = lambda *v: struct.pack('<%dd' % len(v), *v)
ed_.append((gl[0][2], 24, pk(no[0], no[1], o[2]))); ed_.append((gd[0][2], 24, pk(nd[0], nd[1], d[2])))
z = o[2]
for i, l in enumerate(po):
    sg = (0, 1, -1, 0)[i]; ed_.append((l[2], 24, pk(no[0] + sg * t * n[0], no[1] + sg * t * n[1], z)))
for l in px:
    xv = dbl(l[2], 3); r = R(xv[0], xv[1]); ed_.append((l[2], 24, pk(r[0], r[1], xv[2])))
T = ed.g.template(eid); hl = {k: (off, e) for k, off, e, _ in T['hlog']}
if 'Outline.m_minmax' not in hl: sys.exit('REFUSED: no cached outline in the header')
ho = hl['Outline.m_minmax'][0]; bb = struct.unpack_from('<6d', T['hdr'], ho)
q0 = P(*p0); q1 = P(*p1); cs = [(q[0] + s * t * n[0], q[1] + s * t * n[1]) for q in (q0, q1) for s in (-1, 1)]
nbb = (min(c[0] for c in cs), min(c[1] for c in cs), bb[2], max(c[0] for c in cs), max(c[1] for c in cs), bb[5])
hdr = bytearray(T['hdr']); struct.pack_into('<6d', hdr, ho, *nbb)
ed._rec_edit(eid, ed_); ed.g.replace_existing(eid, hdr=bytes(hdr)); ed.save(dst)
print('OK rotated %d by %g deg about (%.4f,%.4f); origin %s dir %s box %s' % (eid, deg, cx, cy, [round(x, 4) for x in no], [round(x, 4) for x in nd], [round(x, 4) for x in nbb]))
