"""Moving hosted window 301610 (house3) +0.5 ft must shift BOTH stored copies of its world origin (record Trf.m_or and the zone-item copy), like Revit's own MoveElement (VM win_mv: both 12.0 -> 12.5).
Before the fix the zone-item copy stayed at 12.0 because the origin lies just outside the cached outline box (z=-0.002) (c1x-rvtdiff 2026-11-16). Synthetic scene; skipped when absent."""
import os, sys, struct, tempfile, subprocess, shutil
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
SCENE = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
if not os.path.exists(SCENE): print('skip: synthetic scene missing'); sys.exit(0)
import wledit, adiff
def body(p): m = wledit.Editor(p).m; return bytes(m.parts[max(m.parts)]['joined'])
def tri(x): return struct.pack('<ddd', x, -0.04265091863520769, -0.0019685039370229696)
d = tempfile.mkdtemp(); ok = False
try:
    out = d + '/w.rte'
    r = subprocess.run(['rvt-ballet', 'edit', SCENE, '-o', out, '--move', '301610', '0.5', '0', '0'], capture_output=True, text=True, timeout=900)
    assert os.path.exists(out), r.stdout + r.stderr
    b0, b1 = body(SCENE), body(out)
    assert b0.count(tri(12.0)) == 2 and b0.count(tri(12.5)) == 0, (b0.count(tri(12.0)), b0.count(tri(12.5)))
    assert b1.count(tri(12.0)) == 0 and b1.count(tri(12.5)) == 2, ('stale origin copy', b1.count(tri(12.0)), b1.count(tri(12.5)))
    # no stray writes: the correct move changes about 6 byte runs / 127 bytes; a junk-triple false positive (c1x-rvtdiff 2026-11-16, Structural 589763) adds runs and overlaps real data
    R = adiff.ops(b0, b1, maxda=3000, maxdb=20000); nb = sum((i1 or i0) - i0 for i0, i1, j0, j1 in R)
    assert len(R) <= 8 and nb <= 300, ('stray writes', len(R), nb)
    ok = True
finally:
    shutil.rmtree(d, ignore_errors=True)
print('hosted window origin copies OK' if ok else 'FAIL'); sys.exit(0 if ok else 1)
