"""Revit 2024 VM (rbnest1): moving a nested parent alone leaves its sub-component behind. The membership check must flag the parent (Autodesk Snowdon Facades 2024, 593273 with child 593274)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
F = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/c2x-tmp/ip25/2024_46_Snowdon_Towers_Sample_Facades.rvt')
m = save.membership(open(F, 'rb').read(), {593273, 593274})
r = save.risky_membership(m, [{'op': 'move', 'eid': 593273}])
assert any(x.startswith('nesting parent of ') for x in r.get(593273, [])), r
assert not save.risky_membership(m, [{'op': 'set_param', 'eid': 593273}]).get(593273), 'parameter edit must not be flagged'
print('ok')
