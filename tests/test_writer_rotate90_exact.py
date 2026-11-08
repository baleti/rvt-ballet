"""writer rotate by 90 degrees stores exact 0/1 in the rotation matrix like Revit (not cos(90)=6.1e-17). Uses local Autodesk-sample ~/c2x-cols2.rvt; skips if absent."""
import os, sys, subprocess, tempfile, json
S = os.path.expanduser('~/c2x-cols2.rvt'); R = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py'); T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_diff.py')
if not (os.path.exists(S) and os.path.exists(R)): print('skip'); sys.exit(0)
d = tempfile.mkdtemp(); o = d + '/o.rvt'
subprocess.run([sys.executable, R, S, o, 'rot:301592:90'], check=True, capture_output=True, timeout=300)
subprocess.run([sys.executable, T, S, o, '--json', d + '/d.json'], capture_output=True, timeout=300)
j = json.load(open(d + '/d.json')); txt = json.dumps(j)
assert '6.123233995736766e-17' not in txt, 'inexact cos(90) written'
assert '[0.0, 1.0, 0.0]' in txt, 'exact RefDir missing'
print('rotate90 exact OK')
