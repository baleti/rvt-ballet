"""compare the viewer's geometry with Revit oracle files (rvt-research/gt_geom): per element bbox IoU, volume ratio, Hausdorff estimate -> <model dir>/compare.json (shown by the viewer's Compare button).
Oracle format (any *.tsv in GTDIR, optionally one model per file; rows may be mixed with E/P rows):
    G <elementId> <minx> <miny> <minz> <maxx> <maxy> <maxz> <volume> [area]          (feet, Revit internal units)
and optionally GTDIR/<elementId>.obj (or GTDIR/<model stem>/<elementId>.obj): oracle mesh in feet, used for the Hausdorff estimate.
usage: tools/compare_gt.py MODELDIR GTDIR   (MODELDIR = converted model directory, e.g. ~/.cache/rvt-viewer/models/<name>)"""
import sys, os, json, glob, pickle
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtviewer import reader, build

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
    G = load_g(gtdir); out = {}; stem = os.path.splitext(os.path.basename(src))[0]
    for i, el in enumerate(els):
        g = G.get(el['id'])
        if g is None or i not in got: continue
        _, fid, kind, parts = got[i]
        if kind != 'tri': continue
        V = np.vstack([p[0] for p in parts]); F = np.vstack([p[1] + sum(len(q[0]) for q in parts[:k]) for k, p in enumerate(parts)])
        lo, hi = V.min(0), V.max(0); r = {'fid': fid, 'iou': round(build.box_iou(lo, hi, np.array(g['bb'][0]), np.array(g['bb'][1])), 3)}
        if g['vol']:
            vol = abs(np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6); r['vratio'] = round(vol / g['vol'], 3)
        for cand in (os.path.join(gtdir, '%d.obj' % el['id']), os.path.join(gtdir, stem, '%d.obj' % el['id'])):
            if os.path.exists(cand):
                OV, OF = read_obj(cand); A = sample(V, F); B = sample(OV, OF)
                dab = cKDTree(B).query(A)[0]; dba = cKDTree(A).query(B)[0]; r['hausdorff_ft'] = round(float(max(dab.max(), dba.max())), 3); r['mean_dev_ft'] = round(float((dab.mean() + dba.mean()) / 2), 4); break
        out[i] = r
    json.dump({'gt': gtdir, 'n': len(out), 'elements': out}, open(os.path.join(mdir, 'compare.json'), 'w'))
    ious = [v['iou'] for v in out.values()]
    print('compared', len(out), 'elements; median IoU', round(float(np.median(ious)), 3) if ious else None)

if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
