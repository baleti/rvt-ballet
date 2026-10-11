"""per-class acceptance metrics for one .rvt (ACCEPTANCE.md): fidelity buckets (true / parametric-unproven / approximate / box-only) and accuracy against Revit's own numbers
(gt4 Volume, header bbox, gt_geom oracle when present).  Writes ~/.cache/rvt-viewer/accept/<year>_<stem>.json.   usage: tools/accept_eval.py FILE.rvt   (run under tools/capped.sh)"""
import sys, os, json, re, glob, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from rvtviewer import reader, build, cli

OUT = os.path.join(reader.CACHE_DIR, 'accept')


def gt4_volumes(path):
    year = os.path.basename(os.path.dirname(path)); stem = os.path.basename(path)
    f = os.path.expanduser('~/rvt-research/gt4/%s_%s.tsv' % (year, stem))
    V = {}
    if not os.path.exists(f): return V, False
    for l in open(f, errors='ignore'):
        x = l.rstrip('\n').split('\t')
        if x[0] == 'P' and len(x) > 5 and x[3] == 'Volume' and x[4] == 'Double':
            try: V[int(x[1])] = float(x[5])
            except ValueError: pass
    return V, True


def main(path):
    os.makedirs(OUT, exist_ok=True)
    year = os.path.basename(os.path.dirname(path)); stem = os.path.splitext(os.path.basename(path))[0]
    import gc
    raw = reader.cached_load(path); ctx = build.Ctx(raw); del raw; ctx.src = path
    els = build.build_table(ctx); ctx._rm = None
    build.ensure_roofs(ctx); gc.collect()
    vols, has_gt = gt4_volumes(path)
    cls = collections.defaultdict(lambda: {'n': 0, 'true': 0, 'param_match': 0, 'approx': 0, 'box': 0, 'vol_n': 0, 'vol_ok': 0, 'vol_ratios': [], 'iou_n': 0, 'iou_ok': 0})
    for i, el in enumerate(els):
        if not el['cat'] or el['isType']: continue
        if i % 200 == 0:
            gc.collect(); rss = int(open('/proc/self/statm').read().split()[1]) * 4096 / 1e9
            if rss > float(os.environ.get('RVT_RSS_BUDGET', '3.3')): print('ABORT %s: RSS %.1f GB over budget' % (os.path.basename(path), rss)); sys.exit(3)
        try: r_ = build.element_mesh(ctx, el['id'], ctx.recs[el['id']])      # one element at a time: nothing is kept after its metrics are taken
        except Exception: r_ = None
        if r_ is None: continue
        mesh, fid = r_
        if getattr(mesh, 'kind', 'tri') != 'tri': continue
        parts = [(pm.v, pm.f) for pm, _ in (mesh.parts if hasattr(mesh, 'parts') else [(mesh, None)])]; kind = 'tri'
        c = cls[el['cls']]; c['n'] += 1
        V = mesh.v; F = mesh.f
        bb = el['bb']
        iou = build.box_iou(V.min(0), V.max(0), *bb) if bb is not None else None
        if fid in ('solid', 'mesh'): c['true'] += 1
        elif fid == 'param' and iou is not None and (iou >= 0.97 or build.contained_match(V.min(0), V.max(0), *bb)): c['param_match'] += 1
        elif fid == 'bbox': c['box'] += 1
        else: c['approx'] += 1
        del mesh, parts, r_
        if iou is not None: c['iou_n'] += 1; c['iou_ok'] += int(iou >= 0.95)
        v = vols.get(el['id'])
        if v and v > 1e-6:
            vol = abs(np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6)
            c['vol_n'] += 1; c['vol_ok'] += int(abs(vol / v - 1) <= 0.02); c['vol_ratios'].append(round(float(vol / v), 4))
    out = {'file': os.path.basename(path), 'year': year, 'has_gt4': has_gt, 'elements': len(els), 'classes': {k: {**v, 'vol_ratios': v['vol_ratios'][:400]} for k, v in cls.items()}}
    json.dump(out, open(os.path.join(OUT, '%s_%s.json' % (year, stem)), 'w'))
    print('OK', year, stem, len(cls), 'classes')


if __name__ == '__main__': main(os.path.abspath(sys.argv[1]))
