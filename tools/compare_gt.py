"""compare the viewer's geometry with Revit oracle files (rvt-research/gt_geom): per element bbox IoU, volume ratio, Hausdorff estimate -> <model dir>/compare.json (shown by the viewer's Compare button).
Oracle format (any *.tsv in GTDIR, optionally one model per file; rows may be mixed with E/P rows):
    G <elementId> <minx> <miny> <minz> <maxx> <maxy> <maxz> <volume> [area]          (feet, Revit internal units)
and optionally GTDIR/<elementId>.obj (or GTDIR/<model stem>/<elementId>.obj): oracle mesh in feet, used for the Hausdorff estimate.
usage: tools/compare_gt.py MODELDIR GTDIR   (MODELDIR = converted model directory, e.g. ~/.cache/rvt-ballet/models/<name>)"""
import sys, os, json, glob, pickle
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import reader, build

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
    if any(len(v) == 1 for v in E.values()): return float('nan')      # open surface (boundary edges): its signed volume depends on the origin, not defined
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
def _vol(V, F):
    """volume of a (possibly inconsistently wound) triangle mesh: weld vertices, orient every connected component consistently (oriented_volume); the reader's rvt_mesh.mesh_volume gave 0.5-0.7 of the true volume on Revit beams with non-manifold edges (verified against Revit's solid volumes to 4 digits, 2026-10-16)"""
    try: return oriented_volume(V, F)
    except Exception: return abs(np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6)

def _xyz(t): return [float(v) for v in t.split(',')]

def load_oracle(gtdir, stem=None):
    """session-181 gt_geom format (FORMAT.md): BB rows (id, min, max as x,y,z) and G rows (key=<id>.<depth>.<solid>, volume=..); depth-0 solids are summed per element"""
    G = {}; seen_sig = set()
    for f in glob.glob(os.path.join(gtdir, '*.tsv')):
        if stem and stem not in os.path.basename(f): continue
        for l in open(f, errors='ignore'):
            x = l.rstrip('\n').split('\t')
            if x[0] == 'BB' and len(x) >= 4 and x[2] != 'null':
                try: G.setdefault(int(x[1]), {})['bb'] = [_xyz(x[2]), _xyz(x[3])]
                except ValueError: pass
            elif x[0] == 'G' and len(x) >= 3:
                k = x[1].split('.')
                try:
                    sig = (k[0], k[1], round(float(x[2].split('=')[1]), 4), round(float(x[3].split('=')[1]), 3) if len(x) > 3 and '=' in x[3] else None, tuple(round(float(c), 3) for c in x[4].split('=')[1].split(',')) if len(x) > 4 and '=' in x[4] else None)      # tolerance: copies of one solid differ in the 6th digit (volume 0.128071 vs 0.128080)      # coincident duplicate solids (same volume, area, centroid; only the material differs, e.g. duct fittings with 3 copies): the viewer drops duplicate bodies on purpose, so the oracle counts them once
                    if sig in seen_sig: continue
                    seen_sig.add(sig)
                    d = G.setdefault(int(k[0]), {}); vol = float(x[2].split('=')[1]); d.setdefault('vd', {}).setdefault(k[1], 0.0); d['vd'][k[1]] += vol; d.setdefault('ad', {}).setdefault(k[1], 0.0); d['ad'][k[1]] += float(x[3].split('=')[1])
                except (ValueError, IndexError): pass
    return {i: {'bb': v.get('bb'), 'vol': (v['vd'][min(v['vd'], key=int)] if v.get('vd') else None), 'area': (v['ad'][min(v['ad'], key=int)] if v.get('ad') else None)} for i, v in G.items() if v.get('bb')}      # solids of the shallowest depth present (family instances are depth 1)

def load_g(gtdir):
    G = {}
    for f in glob.glob(os.path.join(gtdir, '**', '*.tsv'), recursive=True):
        for l in open(f, errors='ignore'):
            if not l.startswith('G\t'): continue
            x = l.rstrip('\n').split('\t')
            try: G[int(x[1])] = {'bb': [[float(v) for v in x[2:5]], [float(v) for v in x[5:8]]], 'vol': float(x[8]) if len(x) > 8 and x[8] != '' else None}
            except ValueError: pass
    return G

def read_obj(fn):
    V = []; F = []
    for l in open(fn):
        if l.startswith('v '): V.append([float(a) for a in l.split()[1:4]])
        elif l.startswith('f '): F.append([int(t.split('/')[0]) - 1 for t in l.split()[1:4]])
    return np.array(V), np.array(F, int)

def sample(V, F, n=2000):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]; ar = np.linalg.norm(np.cross(b - a, c - a), axis=1) + 1e-12
    i = np.random.default_rng(0).choice(len(F), n, p=ar / ar.sum()); u = np.random.default_rng(1).random((n, 2)); u[u.sum(1) > 1] = 1 - u[u.sum(1) > 1]
    return a[i] + u[:, :1] * (b[i] - a[i]) + u[:, 1:] * (c[i] - a[i])

def main(mdir, gtdir):
    from scipy.spatial import cKDTree
    meta = json.load(open(os.path.join(mdir, 'meta.json'))); sm = json.load(open(os.path.join(mdir, 'summary.json')))
    src = sm['src']; raw = reader.cached_load(src); ctx = build.Ctx(raw); ctx.src = src
    els = build.build_table(ctx); ctx.raw_key = '%s|%s|%s|%s' % (os.path.abspath(src), os.path.getmtime(src), os.path.getsize(src), reader.reader_stamp())
    prog = build.Progress(mdir + '.cmp', lambda *a: None) if False else None
    class _P:
        def set(self, *a, **k): pass
    res = build.run_geometry(ctx, els, _P()); got = {t[0]: t for t in res}
    G = load_oracle(gtdir, os.path.splitext(os.path.basename(src))[0]) or load_g(gtdir); out = {}; stem = os.path.splitext(os.path.basename(src))[0]
    for i, el in enumerate(els):
        g = G.get(el['id'])
        if g is None or i not in got: continue
        fid, kind, parts = got[i][1:4]
        if kind == 'line':
            V = np.vstack([p[0] for p in parts]); out[i] = {'fid': fid, 'iou': round(build.box_iou(V.min(0) - 1e-3, V.max(0) + 1e-3, np.array(g['bb'][0]) - 1e-3, np.array(g['bb'][1]) + 1e-3), 3)}; continue
        if kind != 'tri': continue
        V = np.vstack([p[0] for p in parts]); F = np.vstack([p[1] + sum(len(q[0]) for q in parts[:k]) for k, p in enumerate(parts)])
        lo, hi = V.min(0), V.max(0); r = {'fid': fid, 'iou': round(build.box_iou(lo, hi, np.array(g['bb'][0]), np.array(g['bb'][1])), 3)}
        if g['vol']:
            vol = _vol(V, F)
            if vol == vol: r['vratio'] = round(vol / g['vol'], 3)
        r['id'] = el['id']; r['mesh_area'] = round(float(np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1).sum() / 2), 4)
        if g.get('area'): r['aratio'] = round(r['mesh_area'] / g['area'], 3)
        for cand in (os.path.join(gtdir, '%d.obj' % el['id']), os.path.join(gtdir, stem, '%d.obj' % el['id'])):
            if os.path.exists(cand):
                OV, OF = read_obj(cand); A = sample(V, F); B = sample(OV, OF)
                dab = cKDTree(B).query(A)[0]; dba = cKDTree(A).query(B)[0]; r['hausdorff_ft'] = round(float(max(dab.max(), dba.max())), 3); r['mean_dev_ft'] = round(float((dab.mean() + dba.mean()) / 2), 4); break
        out[i] = r
    json.dump({'gt': gtdir, 'n': len(out), 'elements': out}, open(os.path.join(mdir, 'compare.json'), 'w'))
    ious = [v['iou'] for v in out.values()]
    print('compared', len(out), 'elements; median IoU', round(float(np.median(ious)), 3) if ious else None)

if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
