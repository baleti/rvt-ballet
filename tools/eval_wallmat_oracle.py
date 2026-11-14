"""eval_wallmat.py ORACLE_TSV RVT: walls-red-material vs the Revit VM oracle (tools/rvt_wallmat_oracle): layer materials per type, colours per material,
final wall set, all with the same red rule (fastquery.is_red)"""
import sys, os, collections
sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
from rvtballet import fastquery as Q
orc, rvt = sys.argv[1], sys.argv[2]
W = {}; T = {}; M = {}
for l in open(orc, encoding='utf-8', errors='replace'):
    p = l.rstrip('\r\n').split('\t')
    if p[0] == 'W': W[int(p[1])] = (int(p[2]), float(p[3]), p[4])
    elif p[0] == 'T': T[int(p[1])] = [int(x) for x in p[3].split(',') if x] if len(p) > 3 else []
    elif p[0] == 'M':
        cols = []
        for kv in p[2].split(' '):
            if '=' not in kv: continue
            k, v = kv.split('=', 1)
            if k == 'asset' or v in ('-', ''): continue
            try: xs = [float(x) for x in v.split(',')]
            except ValueError: continue
            if k.startswith('app') and len(xs) != 4: continue
            cols.append((k, xs[:3] if k.startswith('app') else [int(x) for x in xs[:3]]))
        M[int(p[1])] = cols
LIM = 5 / 0.3048
red_o = {m for m, cs in M.items() if any(Q.is_red(c) for _, c in cs)}
ans_o = {w for w, (t, h, k) in W.items() if h < LIM and any(m in red_o for m in T.get(t, []))}
import colorsys
def colourful(c):
    r_, g_, b_ = [x / 255.0 if max(c[:3]) > 1 else x for x in c[:3]]; h, s_, v = colorsys.rgb_to_hsv(r_, g_, b_); return s_ >= 0.2 and v >= 0.2
def warm(c):
    r_, g_, b_ = [x / 255.0 if max(c[:3]) > 1 else x for x in c[:3]]; h, s_, v = colorsys.rgb_to_hsv(r_, g_, b_); return (h * 360 <= 60 or h * 360 >= 300) and s_ >= 0.15
r = Q.walls_red_material(rvt, workers=6)
ours = {x['id'] for x in r['rows']}
# step checks
G = Q._G
print(os.path.basename(rvt))
print('  walls: oracle %d ours %d' % (len(W), r['walls']))
print('  red materials: oracle %d ours %d both %d' % (len(red_o), len(r['red']), len(red_o & set(r['red']))))
print('  answer: oracle %d ours %d both %d | %s' % (len(ans_o), len(ours), len(ans_o & ours), 'EQUAL' if ans_o == ours else 'DIFF'))
if red_o != set(r['red']):
    for m in sorted(red_o ^ set(r['red']))[:6]:
        print('   material', m, 'oracle red' if m in red_o else 'ours red', 'oracle props', [k for k, c in M.get(m, []) if Q.is_red(c)][:4], 'ours props', [k for k, c in r['red'].get(m, [])][:4])

# strict step checks: layers per type, colour values per material
lt = sum(1 for t, ms in T.items() if t in r['_types']); le = sum(1 for t, ms in T.items() if t in r['_types'] and [L[2] for L in (r['_types'][t] or [])] == ms)
print('  type layer material lists: oracle types %d, decoded %d, equal %d' % (len(T), lt, le))
def norm(cs, app):
    return sorted(tuple(round(x, 3) for x in c[:3]) if app(k) else tuple(int(x) for x in c[:3]) for k, c in cs)
ce = cn = 0
for m, cs in M.items():
    if m not in r['_colors']: continue
    cn += 1
    a = norm(cs, lambda k: k.startswith('app')); b = norm([(k, c) for k, c in r['_colors'][m] if k != 'asset m_color' and not k.startswith('owned')], lambda k: k.startswith('app'))
    ce += a == b
print('  material colour value sets equal: %d of %d (oracle %d materials)' % (ce, cn, len(M)))
for nm, pr in (('colourful s>=0.2', colourful), ('warm hue', warm)):
    ro = {m for m, cs in M.items() if any(pr(c) for _, c in cs)}; ao = {w for w, (t, h, k) in W.items() if h < LIM and any(m in ro for m in T.get(t, []))}
    rr = Q.walls_red_material(rvt, workers=6, pred=pr); ou = {x['id'] for x in rr['rows']}
    print('  predicate %-17s: oracle %d walls, ours %d, both %d | %s' % (nm, len(ao), len(ou), len(ao & ou), 'EQUAL' if ao == ou else 'DIFF'))
