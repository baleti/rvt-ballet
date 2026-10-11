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
    d = cli.ensure(path, False, log=lambda *a: None)
    meta = json.load(open(os.path.join(d, 'meta.json'))); sm = json.load(open(os.path.join(d, 'summary.json')))
    raw = reader.cached_load(path); ctx = build.Ctx(raw); ctx.src = path
    els = build.build_table(ctx); ctx.raw_key = '%s|%s|%s|%s' % (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path), reader.reader_stamp())
    class _P:
        def set(self, *a, **k): pass
    res = build.run_geometry(ctx, els, _P()); got = {t[0]: t for t in res}
    vols, has_gt = gt4_volumes(path)
    cls = collections.defaultdict(lambda: {'n': 0, 'true': 0, 'param_match': 0, 'approx': 0, 'box': 0, 'vol_n': 0, 'vol_ok': 0, 'vol_ratios': [], 'iou_n': 0, 'iou_ok': 0})
    for i, el in enumerate(els):
        t = got.get(i)
        if t is None or el['isType']: continue
        _, fid, kind, parts = t
        if kind != 'tri': continue
        c = cls[el['cls']]; c['n'] += 1
        V = np.vstack([p[0] for p in parts]); F = np.vstack([p[1] + sum(len(q[0]) for q in parts[:k]) for k, p in enumerate(parts)])
        bb = el['bb']
        iou = build.box_iou(V.min(0), V.max(0), *bb) if bb is not None else None
        if fid in ('solid', 'mesh'): c['true'] += 1
        elif fid == 'param' and iou is not None and (iou >= 0.97 or build.contained_match(V.min(0), V.max(0), *bb)): c['param_match'] += 1
        elif fid == 'bbox': c['box'] += 1
        else: c['approx'] += 1
        if iou is not None: c['iou_n'] += 1; c['iou_ok'] += int(iou >= 0.95)
        v = vols.get(el['id'])
        if v and v > 1e-6:
            vol = abs(np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6)
            c['vol_n'] += 1; c['vol_ok'] += int(abs(vol / v - 1) <= 0.02); c['vol_ratios'].append(round(float(vol / v), 4))
    out = {'file': os.path.basename(path), 'year': year, 'has_gt4': has_gt, 'elements': len(els), 'classes': {k: {**v, 'vol_ratios': v['vol_ratios'][:400]} for k, v in cls.items()}}
    json.dump(out, open(os.path.join(OUT, '%s_%s.json' % (year, stem)), 'w'))
    print('OK', year, stem, len(cls), 'classes')


if __name__ == '__main__': main(os.path.abspath(sys.argv[1]))
