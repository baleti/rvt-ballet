"""Compare rebuilt geometry against Revit-computed parameters in ground-truth dumps (rvt-research/gt4/*.tsv, produced by real Revit).
usage: verify_gt.py FILE.rvt GT.tsv   -> volume / area / length agreement per class (our parametric solids vs Revit's values; Revit subtracts openings and joins)"""
import sys, os, collections, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import reader, build

def mesh_volume(m):
    v = m.v; f = m.f
    return abs(np.einsum('ij,ij->i', v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6.0)

def load_gt(path):
    cls = {}; vals = collections.defaultdict(dict)
    for l in open(path, errors='ignore'):
        x = l.rstrip('\n').split('\t')
        if x[0] == 'E': cls[int(x[1])] = (x[2], x[3])
        elif x[0] == 'P' and len(x) > 5 and x[3] in ('Volume', 'Area', 'Length', 'Unconnected Height', 'Width') and x[4] == 'Double':
            try: vals[int(x[1])][x[3]] = float(x[5])
            except ValueError: pass
    return cls, vals

def main(rvt, gt):
    raw = reader.cached_load(rvt); ctx = build.Ctx(raw); cls, vals = load_gt(gt)
    rows = collections.defaultdict(lambda: collections.defaultdict(list))
    for e, r in ctx.recs.items():
        if e not in vals: continue
        res = build.element_mesh(ctx, e, r)
        if not res or res[1] not in ('param', 'solid'): continue
        m = res[0]
        if hasattr(m, 'kind'): continue
        c = r['class']; V = mesh_volume(m)
        if 'Volume' in vals[e] and vals[e]['Volume'] > 1e-6: rows[c]['Volume'].append(V / vals[e]['Volume'])
        if 'Length' in vals[e] and vals[e]['Length'] > 1e-6 and c in ('SWall',):
            bb = m.v.max(0) - m.v.min(0); rows[c]['LengthXY'].append(max(bb[0], bb[1]) / vals[e]['Length'])
        if 'Unconnected Height' in vals[e] and c == 'SWall': rows[c]['Height'].append((m.v[:, 2].max() - m.v[:, 2].min()) / vals[e]['Unconnected Height'])
    out = {}
    for c, d in rows.items():
        for k, v in d.items():
            a = np.array(v); out['%s.%s' % (c, k)] = {'n': len(a), 'median_ratio': round(float(np.median(a)), 3), 'within5%': round(float(np.mean(np.abs(a - 1) < 0.05)), 3), 'within15%': round(float(np.mean(np.abs(a - 1) < 0.15)), 3)}
    for k, v in sorted(out.items()): print(k, v)
    return out

if __name__ == '__main__': main(sys.argv[1], sys.argv[2])
