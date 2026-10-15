"""cross-check the viewer's B-rep tessellation (rvtviewer.brep) against the reader's rvt_mesh.tessellate_geometry: triangle counts and signed volume per Geometry body.
usage: tools/check_mesh.py FILE.rvt"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import numpy as np
import rvt_mesh as RM
from rvtviewer import reader, build, brep
ctx = build.Ctx(reader.cached_load(sys.argv[1])); n = ok = 0
for e, r in ctx.recs.items():
    if r['class'].startswith(('DBView', 'Analytical')): continue
    for gm in brep.find_geometries(r['fields']):
        if len(gm['m_pFaces']) < 4: continue
        m, nf, sk = brep.geometry_mesh(gm); t = RM.tessellate_geometry(gm)
        if not m: continue
        v = abs(np.einsum('ij,ij->i', m.v[m.f[:, 0]], np.cross(m.v[m.f[:, 1]], m.v[m.f[:, 2]])).sum() / 6)
        n += 1; same = abs(len(t['tris']) - len(m.f)) <= max(2, 0.05 * len(m.f)); ok += same
        if not same or n <= 3: print(e, r['class'], 'mine tris', len(m.f), 'reader tris', len(t['tris']), 'unsupported', t['unsupported'][:3], 'my skipped', sk)
print('bodies', n, 'triangle counts agree', ok)
