"""tools/hl_soft_all.py NAME MODELDIR: software hidden-line render + registered line F1 for every HLR view (cameras.tsv style=HLR) of ~/review-compare/revit/NAME (browser free, run on host1 via h1run env rvt:
numpy + numba + scipy + PIL). Needs ~/review-compare/vg3d/NAME/<vid>.json (tools/hl_soft_prep.py). Writes ~/review-compare/viewer/NAME/<vid>__soft.png and prints the table."""
import sys, os, subprocess
H = os.path.expanduser('~'); name, model = sys.argv[1], sys.argv[2]; D = os.path.dirname(os.path.abspath(__file__)); R = '%s/review-compare/revit/%s' % (H, name); O = '%s/review-compare/viewer/%s' % (H, name)
os.makedirs(O, exist_ok=True); rows = []
for l in open(R + '/cameras.tsv'):
    if l[0] == '#' or 'style=HLR' not in l: continue
    vid = l.split('\t')[0]; vg = '%s/review-compare/vg3d/%s/%s.json' % (H, name, vid); out = '%s/%s__soft.png' % (O, vid)
    if not os.path.exists(R + '/%s.png' % vid): continue
    a = [sys.executable, D + '/hl_soft.py', model, R + '/cameras.tsv', vid, out] + (['--vg', vg] if os.path.exists(vg) else [])
    p = subprocess.run(a, capture_output=True, text=True)
    if p.returncode: print(vid, 'render failed', p.stderr[-200:]); continue
    q = subprocess.run([sys.executable, D + '/hl_score.py', R + '/%s.png' % vid, out], capture_output=True, text=True)
    if q.returncode: print(vid, 'score failed', q.stderr[-200:]); continue
    s = q.stdout.strip(); print(name, vid, 'vg' if os.path.exists(vg) else 'NO-VG', s, flush=True); rows.append(s)
import re
f1 = [float(m.group(1)) for r in rows for m in [re.search(r'F1 ([\d.]+)', r)] if m]
if f1: print('%s mean F1 %.3f over %d HLR views' % (name, sum(f1) / len(f1), len(f1)))
