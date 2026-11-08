"""Moving a Level that has associated elements is flagged 'level constrains N element(s)' (Revit carries level-relative elements with the level; the writer moves the Level record only), so the in-place SAVE! refuses. Autodesk Snowdon HVAC 2024 Level 9946 (hundreds of associated elements); parameter edit not flagged. Skipped if absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
F = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(F): print('skip'); sys.exit(0)
from rvtballet import save
m = save.membership(open(F, 'rb').read(), [9946])
assert any(w.startswith('level constrains') for w in m.get(9946, [])), m
assert 9946 in save.risky_membership(m, [{'op': 'move', 'eid': 9946}])
assert 9946 not in save.risky_membership(m, [{'op': 'set_string', 'eid': 9946}])
print('level move with dependents flagged:', m[9946])
