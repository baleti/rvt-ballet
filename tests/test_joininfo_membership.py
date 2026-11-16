"""c1x-rvtmove 2026-11-16: FamilyInstances named only through another instance's m_JoinInfo / m_otherInfoAtMiter (Snowdon Structural 2024: 686385, 793186, 793190, 797279) are flagged as joined, so an in-place move is refused; an unjoined synthetic column (cols2 301595) stays unflagged. Local samples; skipped without them."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
A = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt'); B = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not (os.path.exists(A) and os.path.exists(B)): print('skip'); sys.exit(0)
from rvtballet import save
ids = [686385, 793186, 793190, 797279]
m = save.membership(open(A, 'rb').read(), ids)
r = save.risky_membership(m, [{'op': 'move', 'eid': i} for i in ids])
assert set(r) == set(ids), (m, r)
assert save.membership(open(B, 'rb').read(), [301595]) == {}
print('join/miter membership OK')
