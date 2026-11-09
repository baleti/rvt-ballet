"""Joined walls: Revit's own move of Site 2024 wall 1139388 (+1 ft x) also rewrote 7 joined neighbours (end params, envelopes, edge points); the writer moves only the wall. membership() must flag the wall as 'joined to N element(s)' and risky_membership must keep it for a move/rotate (so overwrite is refused, Save As warns) but not for a parameter edit. Fails without the joined detector."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/47_Snowdon_Towers_Sample_Site.rvt')
from rvtballet import save
if not os.path.exists(SRC): print('SKIP: sample absent'); sys.exit(0)
b = open(SRC, 'rb').read()
m = save.membership(b, [1139388])
assert any(x.startswith('joined to') for x in m.get(1139388, [])), m
assert 1139388 in save.risky_membership(m, [{'op': 'move', 'eid': 1139388}])
assert 1139388 in save.risky_membership(m, [{'op': 'rotate', 'eid': 1139388}])
assert 1139388 not in save.risky_membership(m, [{'op': 'set_string', 'eid': 1139388}])
print('OK')
