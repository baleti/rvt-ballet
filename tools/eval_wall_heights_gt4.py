import sys, os
sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
from rvtballet import fastquery as Q
tot = [0, 0, 0, 0]
for f in sys.argv[1:]:
    y = f.split('_')[0]; r = f[len(y) + 1:]
    gt = os.path.expanduser('~/rvt-research/gt4/%s.rvt.tsv' % f); rvt = os.path.expanduser('~/rvt-research/corpus/%s/%s.rvt' % (y, r))
    H = {}; L = {}
    for l in open(gt, errors='replace'):
        p = l.rstrip('\n').split('\t')
        if p[0] == 'P' and p[2] == '-1001105':
            try: H[int(p[1])] = float(p[5])
            except (ValueError, IndexError): pass
    rows = Q.collect(rvt, 'Wall', fields=['params', 'm_assocLevelId', 'm_upToLevelId'], workers=6); lv = Q.collect(rvt, 'Level', fields=['elevation'], workers=6)
    elev = {x['id']: x['elevation'] for x in lv if x.get('elevation') is not None}
    n = ok = below_gt = below_ok = 0
    for x in rows:
        if x['id'] not in H: continue
        h, how = Q.wall_height(x, elev); n += 1
        if isinstance(h, (int, float)) and abs(h - H[x['id']]) < 1e-4: ok += 1
        b = H[x['id']] < 5 / 0.3048; below_gt += b; below_ok += b == (isinstance(h, (int, float)) and h < 5 / 0.3048)
    print('%-45s walls with Revit height %4d, decoded equal %4d, below 5 m (Revit) %4d, below-5m decision equal %4d' % (f, n, ok, below_gt, below_ok), flush=True)
    for i, v in enumerate((n, ok, below_gt, below_ok)): tot[i] += v
print('TOTAL', tot)
