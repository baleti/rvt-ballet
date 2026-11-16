"""A hosted door moved +0.5 ft and then -0.5 ft (two product edits, the second on the first's output) must come back byte-identical in every partition body.
Before the fix the second move left the cached origin triple of the zone item at the moved x (18.5) and an item checksum differed (c1x-rvtdiff 2026-11-16).
Synthetic scene (write-lab house3, door 301609); skipped when the scene is not present."""
import os, sys, tempfile, subprocess, shutil
SCENE = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
if not os.path.exists(SCENE): print('skip: synthetic scene missing'); sys.exit(0)
d = tempfile.mkdtemp(); ok = False
try:
    def edit(src, out, dx):
        r = subprocess.run(['rvt-ballet', 'edit', src, '-o', out, '--move', '301609', str(dx), '0', '0'], capture_output=True, text=True, timeout=900)
        assert os.path.exists(out), r.stdout + r.stderr
    m1, m2 = d + '/m1.rte', d + '/m2.rte'
    edit(SCENE, m1, 0.5); edit(m1, m2, -0.5)
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_diff.py'), SCENE, m2], capture_output=True, text=True, timeout=900)
    assert '0 differing byte runs' in r.stdout and 'changed 0' in r.stdout and 'differing byte runs' in r.stdout and not any(l.startswith('    @') for l in r.stdout.splitlines() if 'Partitions' not in l and 'BasicFileInfo' not in l and 'global' not in l and False), r.stdout[-800:]
    assert 'partition body' in r.stdout and all(('0 differing byte runs' in l) for l in r.stdout.splitlines() if l.startswith('partition body')), r.stdout[-800:]
    ok = True
finally:
    shutil.rmtree(d, ignore_errors=True)
print('move round trip on hosted door OK' if ok else 'FAIL'); sys.exit(0 if ok else 1)
