"""A beam whose end is attached to a support (own m_refs[].m_endStructId, Structural 2024 795822/795823/797227/797228) is flagged for move/rotate, not for parameter edits (Revit VM: MoveElement of 795822 fails 'Can't keep elements joined' and rolls back)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
W = 'attached to support 663713 at an end'
assert save.risky_membership({7: [W]}, [{'op': 'move', 'eid': 7}]) == {7: [W]}
assert save.risky_membership({7: [W]}, [{'op': 'set_string', 'eid': 7}]) == {}
P = os.path.expanduser('~/rvtfix/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
if os.path.exists(P):
    m = save.membership(open(P, 'rb').read(), [795822, 795823, 797227, 797228])
    for e in (795822, 795823, 797227, 797228): assert any(x.startswith('attached to support') for x in m.get(e, [])), (e, m.get(e))
print('attached-beam move guard ok')
