"""c1x-rvtmove 2026-11-16: a Grid that constrains other elements (columns placed at its intersections, GeomRef m_elemId) is flagged 'grid constrains N element(s)' so an in-place move is refused even when no dimension references it. Revit-made grid move on synthetic house3 2024 (grid_mv witness): 6 columns follow, a railing regenerates; the writer moves only the Grid record. Needs the local witness base (skipped without)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
F = os.path.expanduser('~/c2x-diff/grid_mv/base.rte')
if not os.path.exists(F): print('skip'); sys.exit(0)
from rvtballet import save
m = save.membership(open(F, 'rb').read(), [301556])
assert 'grid constrains 6 element(s)' in m.get(301556, []), m
assert 301556 in save.risky_membership(m, [{'op': 'move', 'eid': 301556}])
print('grid constrains membership OK')
