"""A wall that HOSTS doors/windows is flagged when moved or rotated (membership 'hosts N element(s)'): the writer moves the wall only, Revit's own MoveElement would drag the hosted elements along, so an in-place save must refuse. Synthetic write-lab scene 2024_writer_hosted2 (wall 301557 hosts instance 301559, wall 301553 hosts 10). A parameter edit of the host is not flagged."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_hosted2.rte')
from rvtballet import save
if not os.path.exists(F): print('skip: scene not present'); sys.exit(0)
m = save.membership(open(F, 'rb').read(), [301553, 301557, 301559])
exp = {301553: ['dimensioned by 1 dimension(s)', 'hosts 10 element(s)'], 301557: ['hosts 1 element(s)'], 301559: ['hosted on 301557']}
# membership may add further reasons (e.g. 'joined to N element(s)'); the hosting facts must remain
assert all(set(v) <= set(m.get(k, [])) for k, v in exp.items()) and set(m) == set(exp), m
for op in ('move', 'rotate'): assert 301557 in save.risky_membership(m, [{'op': op, 'eid': 301557}])
assert 301557 not in save.risky_membership(m, [{'op': 'set_string', 'eid': 301557}])
print('host wall move/rotate flagged, parameter edit not: OK')
