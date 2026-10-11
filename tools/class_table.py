"""per-class fidelity buckets of a converted model: true geometry (B-rep / saved mesh) | parametric with matching extents | approximate | box only.   usage: tools/class_table.py MODELDIR [N]"""
import sys, json, os
m = json.load(open(os.path.join(sys.argv[1], 'meta.json'))); hid = set(m.get('defaultHidden') or []); N = int(sys.argv[2]) if len(sys.argv) > 2 else 15
rows = []
for cat, v in m['coverageByClass'].items():
    t = v.get('solid', 0) + v.get('mesh', 0); mt = v.get('matched', 0); ap = v.get('param', 0) + v.get('approx', 0); bx = v.get('bbox', 0); n = t + mt + ap + bx
    if n: rows.append((n, cat, t, mt, ap, bx))
print('| class | n | true | param-match | approx | box |\n|---|---|---|---|---|---|')
for n, cat, t, mt, ap, bx in sorted(rows, reverse=True)[:N]: print('| %s | %d | %.0f%% | %.0f%% | %.0f%% | %.0f%% |' % (cat, n, 100 * t / n, 100 * mt / n, 100 * ap / n, 100 * bx / n))
