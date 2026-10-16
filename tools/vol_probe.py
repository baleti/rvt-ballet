"""why does a viewer mesh have another volume than Revit's solid: tools/vol_probe.py CORPUS_FILE ID [ID ...]: plain signed volume, mesh_volume of the reader, volume after welding vertices, edge manifoldness, Revit's gt volume"""
import sys, os, json
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.expanduser('~/rvt-research')); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools'))      # tools/ first: ~/rvt-research has another compare_gt
import compare_gt as C; from rvtviewer import reader, build
src = sys.argv[1]; ids = [int(x) for x in sys.argv[2:]]
raw = reader.cached_load(src); ctx = build.Ctx(raw); ctx.src = src; els = build.build_table(ctx)
ctx.raw_key = '%s|%s|%s|%s' % (os.path.abspath(src), os.path.getmtime(src), os.path.getsize(src), reader.reader_stamp())
class _P:
    def set(self, *a, **k): pass
res = build.run_geometry(ctx, els, _P()); got = {t[0]: t for t in res}
G = C.load_oracle(os.path.expanduser('~/rvt-research/gt_geom'), os.path.splitext(os.path.basename(src))[0])
for i, el in enumerate(els):
    if el['id'] not in ids or i not in got: continue
    fid, kind, parts = got[i][1:4]
    V = np.vstack([p[0] for p in parts]); F = np.vstack([p[1] + sum(len(q[0]) for q in parts[:k]) for k, p in enumerate(parts)])
    T = V[F]; plain = float(np.einsum('ij,ij->i', T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6)
    key = np.round(V, 5); u, inv = np.unique(key, axis=0, return_inverse=True); W = inv.reshape(-1)[F]
    Tw = u[W]; wv = float(np.einsum('ij,ij->i', Tw[:, 0], np.cross(Tw[:, 1], Tw[:, 2])).sum() / 6)
    E = {}
    for a, b, c in W:
        for p, q in ((a, b), (b, c), (c, a)): E.setdefault((min(p, q), max(p, q)), []).append(1 if p < q else -1)
    bad = sum(1 for v in E.values() if len(v) != 2); same = sum(1 for v in E.values() if len(v) == 2 and v[0] == v[1])
    g = G.get(el['id'], {})
    print(el['id'], el['cls'], 'parts', len(parts), 'tris', len(F), 'verts', len(V), 'welded', len(u), '| plain', round(plain, 4), 'welded-plain', round(wv, 4), 'mesh_volume', round(C._vol(V, F), 4), 'gt', g.get('vol'),
          '| edges', len(E), 'non-2-manifold', bad, 'same-direction (flipped) pairs', same)
