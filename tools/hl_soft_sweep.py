"""parameter sweep of the software hidden-line renderer against Revit (host1): tools/hl_soft_sweep.py NAME MODELDIR [VIEWIDS...]
for edge angle x minimum edge length, renders the given HLR views (default: the stable Snowdon ones, not Foundations) and prints the mean registered F1 per configuration, best first.
Needs ~/review-compare/vg3d/NAME/<vid>.json (tools/hl_soft_h1.sh creates them)."""
import sys, os, subprocess, re, itertools
H = os.path.expanduser('~'); name, model = sys.argv[1], sys.argv[2]; D = os.path.dirname(os.path.abspath(__file__)); R = '%s/review-compare/revit/%s' % (H, name)
views = sys.argv[3:] or ['600158', '783844', '783871', '783882', '783925', '923315']
res = []
SKIP = int(os.environ.get('HL_SWEEP_SKIP', 0))      # resume after a killed run: number of leading configurations already done
GRID = [tuple(float(x) for x in g.split(':')) for g in os.environ['HL_SWEEP_GRID'].split(',')] if os.environ.get('HL_SWEEP_GRID') else list(itertools.product((20, 30, 45), (0.0, 0.01, 0.03)))      # HL_SWEEP_GRID=30:0.01,45:0.01
for ang, me in GRID[SKIP:]:
    f1 = []
    for vid in views:
        out = '/tmp/hlsweep_%s_%s_%s.png' % (ang, me, vid); vg = '%s/review-compare/vg3d/%s/%s.json' % (H, name, vid)
        p = subprocess.run([sys.executable, D + '/hl_soft.py', model, R + '/cameras.tsv', vid, out, '--vg', vg, '--angle', str(ang), '--min-edge', str(me)], capture_output=True, text=True)
        if p.returncode: print('render failed', vid, p.stderr[-150:]); continue
        s = subprocess.run([sys.executable, D + '/hl_score.py', R + '/%s.png' % vid, out], capture_output=True, text=True).stdout
        m = re.search(r'F1 ([\d.]+)', s)
        if m: f1.append(float(m.group(1)))
        os.remove(out)
    if f1: res.append((sum(f1) / len(f1), ang, me, f1)); print('angle %d min-edge %.2f mean F1 %.4f %s' % (ang, me, res[-1][0], ' '.join('%.3f' % x for x in f1)), flush=True)
print('BEST', sorted(res, reverse=True)[:3])
