"""A wall referenced by a dimension (LinearDimString witness m_geomRef.m_elemId) is flagged 'dimensioned by N dimension(s)' when moved/rotated, so an in-place save refuses (the writer moves the wall only; the dimension value stays stale). Synthetic write-lab scene 2024_writer_dimensions_after_finish (wall 301598, dims 302093 and 302077). A parameter edit is not flagged."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
F = os.path.expanduser('~/c7x-rm/dimw/orig.rte')
from rvtballet import save
if not os.path.exists(F): print('skip: scene not present'); sys.exit(0)
m = save.membership(open(F, 'rb').read(), [301598])
assert any(w.startswith('dimensioned by') for w in m.get(301598, [])), m
assert 301598 in save.risky_membership(m, [{'op': 'move', 'eid': 301598}])
assert 301598 not in save.risky_membership(m, [{'op': 'set_string', 'eid': 301598}])
print('dimensioned wall move flagged:', m[301598])
