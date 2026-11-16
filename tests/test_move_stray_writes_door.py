"""Stray-write bound for an accepted move of door 301609 (house3 synthetic scene): the changed byte runs must stay small (like the window test).
Catches false-positive anchor matches that overwrite real data (c1x-rvtdiff 2026-11-16, Structural 589763). Skipped when the scene is absent."""
import os, sys, tempfile, subprocess, shutil
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
SCENE = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
if not os.path.exists(SCENE): print('skip: synthetic scene missing'); sys.exit(0)
import wledit, adiff
def body(p): m = wledit.Editor(p).m; return bytes(m.parts[max(m.parts)]['joined'])
MAX_RUNS, MAX_BYTES = int(os.environ.get('MAXR', 8)), int(os.environ.get('MAXB', 300))
d = tempfile.mkdtemp(); ok = False
try:
    out = d + '/w.rte'
    r = subprocess.run(['rvt-ballet', 'edit', SCENE, '-o', out, '--move', '301609', '0.5', '0', '0'], capture_output=True, text=True, timeout=900)
    assert os.path.exists(out), r.stdout + r.stderr
    R = adiff.ops(body(SCENE), body(out), maxda=3000, maxdb=20000); nb = sum((i1 or i0) - i0 for i0, i1, j0, j1 in R)
    print('door move runs', len(R), 'bytes', nb)
    assert len(R) <= MAX_RUNS and nb <= MAX_BYTES, ('stray writes', len(R), nb)
    ok = True
finally:
    shutil.rmtree(d, ignore_errors=True)
print('door move stray-write bound OK' if ok else 'FAIL'); sys.exit(0 if ok else 1)
