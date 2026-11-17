"""Instances named as m_assocId by sketch curves (Structural 2024 774939, 774940) are flagged for move/rotate (Revit VM: its own MoveElement of 774939 +1 ft ended RolledBack), not for parameter edits."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
W = 'associated with sketch curves (m_assocId)'
assert save.risky_membership({7: [W]}, [{'op': 'move', 'eid': 7}]) == {7: [W]}
assert save.risky_membership({7: [W]}, [{'op': 'set_string', 'eid': 7}]) == {}
P = os.path.expanduser('~/rvtfix/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
if os.path.exists(P):
    m = save.membership(open(P, 'rb').read(), [774939, 774940, 606069])
    assert W in m[774939] and W in m[774940], m
    assert W not in ' '.join(m.get(606069, [])), 'a plain tracked column is not sketch-associated'
print('sketch-assoc move guard ok')
