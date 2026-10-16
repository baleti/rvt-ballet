"""why does a viewer mesh have another volume than Revit's solid: tools/vol_probe.py CORPUS_FILE ID [ID ...]: plain signed volume, mesh_volume of the reader, volume after welding vertices, edge manifoldness, Revit's gt volume"""
import sys, os, json
import numpy as np
def oriented_volume(V, F):
    """weld vertices, make the winding consistent per connected component (BFS over edges shared by exactly 2 triangles, flipping faces whose shared edge runs the same direction), then the volume of each component as |signed sum|"""
    key = np.round(V, 5); u, inv = np.unique(key, axis=0, return_inverse=True); W = inv.reshape(-1)[F].copy(); n = len(W)
    E = {}
    for t, (a, b, c) in enumerate(W):
        for p, q in ((a, b), (b, c), (c, a)): E.setdefault((min(p, q), max(p, q)), []).append((t, 1 if p < q else -1))
    adj = [[] for _ in range(n)]
    for v in E.values():
        if len(v) == 2: (t1, d1), (t2, d2) = v; adj[t1].append((t2, d1 == d2)); adj[t2].append((t1, d1 == d2))      # same direction on the shared edge = one of them must flip
    flip = np.zeros(n, bool); seen = np.zeros(n, bool); tot = 0.0
    for s0 in range(n):
        if seen[s0]: continue
        comp = [s0]; seen[s0] = True; k = 0
        while k < len(comp):
            t = comp[k]; k += 1
            for t2, same in adj[t]:
                if not seen[t2]: seen[t2] = True; flip[t2] = flip[t] ^ same; comp.append(t2)
        Tc = u[W[comp]]; sg = np.where(flip[comp], -1.0, 1.0)
        tot += abs(float((np.einsum('ij,ij->i', Tc[:, 0], np.cross(Tc[:, 1], Tc[:, 2])) * sg).sum() / 6))
    return tot
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
    print(el['id'], el['cls'], 'parts', len(parts), 'tris', len(F), 'verts', len(V), 'welded', len(u), '| plain', round(plain, 4), 'welded-plain', round(wv, 4), 'mesh_volume', round(C._vol(V, F), 4), 'ORIENTED', round(oriented_volume(V, F), 4), 'gt', g.get('vol'),
          '| edges', len(E), 'non-2-manifold', bad, 'same-direction (flipped) pairs', same)
