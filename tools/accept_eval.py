"""per-class acceptance metrics for one .rvt (ACCEPTANCE.md): fidelity buckets (true / parametric-unproven / approximate / box-only) and accuracy against Revit's own numbers
(gt4 Volume, header bbox, gt_geom oracle when present).  Writes ~/.cache/rvt-ballet/accept/<year>_<stem>.json.   usage: tools/accept_eval.py FILE.rvt   (run under tools/capped.sh)"""
import sys, os, json, re, glob, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from rvtballet import reader, build, cli

OUT = os.path.join(reader.CACHE_DIR, 'accept')


def _vol(V, F):
    try:
        sys.path.insert(0, os.path.expanduser('~/rvt-research')); import rvt_mesh
        return float(rvt_mesh.mesh_volume([tuple(map(tuple, V[f])) for f in F])[0])
    except Exception: return abs(np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6)

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


def main_mesh(path):
    """low-memory mode for the big files: only the reader's geometry API (no viewer context): buckets for every non-analytic class from element_geometry confidence"""
    os.makedirs(OUT, exist_ok=True)
    year = os.path.basename(os.path.dirname(path)); stem = os.path.splitext(os.path.basename(path))[0]
    reader._import(); import rvt_geometry as GG, gc
    idx = GG.file_geometry_index(path); cls = collections.defaultdict(lambda: {'n': 0, 'true': 0, 'param_match': 0, 'approx': 0, 'box': 0, 'vol_n': 0, 'vol_ok': 0, 'vol_ratios': [], 'iou_n': 0, 'iou_ok': 0, 'acc': 0, 'toff': 0, 'unj': 0})
    skip = ('FamilySymbol', 'Family', 'FamSymSurrogate', 'FamilySurrogate')
    for k, (e, c) in enumerate(idx.items()):
        if c in build.ANALYTIC_CLASSES or c in skip: continue
        if k % 500 == 0:
            gc.collect(); rss = int(open('/proc/self/statm').read().split()[1]) * 4096 / 1e9
            if rss > float(os.environ.get('RVT_RSS_BUDGET', '2.7')): print('ABORT %s: RSS %.1f GB over budget' % (os.path.basename(path), rss)); sys.exit(3)
        try: a = GG.element_geometry(path, e)
        except Exception: continue
        conf = a.get('confidence')
        if conf in (None, 'none'): continue
        d = cls[c]; d['n'] += 1
        if conf == 'mesh_approx':
            d['true' if 'unsupported_faces' not in (a.get('flags') or []) else 'approx'] += 1
            if 'unsupported_faces' not in (a.get('flags') or []): d['unj'] += 1          # mesh mode has no viewer-side volume: unjudged
        elif conf == 'box': d['box'] += 1
        elif conf == 'exact': d['true'] += 1
        else: d['approx'] += 1
    json.dump({'file': os.path.basename(path), 'year': year, 'has_gt4': False, 'elements': len(idx), 'mode': 'mesh', 'classes': dict(cls)}, open(os.path.join(OUT, '%s_%s__mesh.json' % (year, stem)), 'w'))
    print('OK mesh-mode', year, stem, len(cls), 'classes')


def main(path):
    os.makedirs(OUT, exist_ok=True)
    year = os.path.basename(os.path.dirname(path)); stem = os.path.splitext(os.path.basename(path))[0]
    import gc
    raw = reader.cached_load(path); ctx = build.Ctx(raw); del raw; ctx.src = path
    if os.environ.get('RVT_ANALYTIC_ONLY'): build.USE_READER_MESH = False
    els = build.build_table(ctx); ctx._rm = None
    build.ensure_roofs(ctx); gc.collect()
    vols, has_gt = gt4_volumes(path)
    cls = collections.defaultdict(lambda: {'n': 0, 'true': 0, 'param_match': 0, 'approx': 0, 'box': 0, 'vol_n': 0, 'vol_ok': 0, 'vol_ratios': [], 'iou_n': 0, 'iou_ok': 0, 'acc': 0, 'toff': 0, 'unj': 0})
    for i, el in enumerate(els):
        if not el['cat'] or el['isType']: continue
        if os.environ.get('RVT_ANALYTIC_ONLY') and ctx.recs[el['id']]['class'] not in build.ANALYTIC_CLASSES: continue
        if i % 200 == 0:
            gc.collect(); rss = int(open('/proc/self/statm').read().split()[1]) * 4096 / 1e9
            if rss > float(os.environ.get('RVT_RSS_BUDGET', '3.3')): print('ABORT %s: RSS %.1f GB over budget' % (os.path.basename(path), rss)); sys.exit(3)
        try: r_ = build.element_mesh(ctx, el['id'], ctx.recs[el['id']])      # one element at a time: nothing is kept after its metrics are taken
        except Exception: r_ = None
        if r_ is None: continue
        mesh, fid = r_
        if fid == 'void': cls[el['cls']]['void'] = cls[el['cls']].get('void', 0) + 1; continue      # no 3D solid in Revit either (void-only / reference families): its own bucket, not box-only
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
        v = vols.get(el['id']); ok = None                                       # reader definition (NOTES.md per-class table): ACCURATE = Revit Volume within 2 % or, without a volume, bbox IoU >= 0.95
        if v and v > 1e-6:
            vol = _vol(V, F)
            c['vol_n'] += 1; c['vol_ok'] += int(abs(vol / v - 1) <= 0.02); c['vol_ratios'].append(round(float(vol / v), 4)); ok = abs(vol / v - 1) <= 0.02
        elif iou is not None: ok = iou >= 0.95
        if fid in ('solid', 'mesh'):
            if ok is None: c['unj'] += 1
            elif ok: c['acc'] += 1
            else: c['toff'] += 1
    out = {'file': os.path.basename(path), 'year': year, 'has_gt4': has_gt, 'elements': len(els), 'classes': {k: {**v, 'vol_ratios': v['vol_ratios'][:400]} for k, v in cls.items()}}
    json.dump(out, open(os.path.join(OUT, '%s_%s%s.json' % (year, stem, '__analytic' if os.environ.get('RVT_ANALYTIC_ONLY') else '')), 'w'))
    print('OK', year, stem, len(cls), 'classes')


if __name__ == '__main__':
    if '--mesh' in sys.argv: main_mesh(os.path.abspath([a for a in sys.argv[1:] if not a.startswith('--')][0]))
    else: main(os.path.abspath(sys.argv[1]))
