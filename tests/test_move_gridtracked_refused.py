"""A column with a NON-empty GridsForColumn entry (on a grid intersection) is flagged for move/rotate, not for parameter edits: Revit VM (Structural 2024 column 606069 +1 ft x) rewrote the
tracker entry (m_dist 0 -> 1, m_gridIntRefType 0 -> 1); the writer leaves it stale. Public Structural 2024 sample and a pure-function case."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
W = 'on a grid intersection (GridsForColumn entry)'
assert save.risky_membership({7: [W]}, [{'op': 'move', 'eid': 7}]) == {7: [W]}
assert save.risky_membership({7: [W]}, [{'op': 'rotate', 'eid': 7}]) == {7: [W]}
assert save.risky_membership({7: [W]}, [{'op': 'set_string', 'eid': 7}]) == {}
P = os.path.expanduser('~/rvtfix/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
if os.path.exists(P):
    m = save.membership(open(P, 'rb').read(), [606069, 606163, 606268])
    assert all(W in m[e] for e in (606069, 606163, 606268)), m
B = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if os.path.exists(B):
    assert W not in ' '.join(sum(save.membership(open(B, 'rb').read(), [301595]).values(), [])), 'cols2 has only empty entries'
print('grid-tracked move guard ok')
