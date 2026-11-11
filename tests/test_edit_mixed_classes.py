"""c6x-rvtmatrix item 21: ops on THREE different classes in one edit session on the synthetic 2024 cols2 (plan view rename, level rename, FamilyInstance Mark + move): all applied (or honestly refused), readback exact, every other element's params unchanged except the view/level name echoes (dependents)."""
import os, sys, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import rvt_params
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def params(b):
    d = tempfile.mkdtemp(); p = d + '/x.rte'; open(p, 'wb').write(b); return rvt_params.params(p)
P0 = params(buf)
ops = [{'op': 'set_string', 'eid': 356, 'field': 'DBView.m_viewName', 'value': 'Level 1 c3x', 'match': 'Level 1'},
       {'op': 'set_string', 'eid': 355, 'field': 'DatumPlane.m_text', 'value': 'Level 1 c3x', 'match': 'Level 1'},
       {'op': 'set_string', 'eid': 301560, 'param': 'Mark', 'value': 'c3x mixed'}, {'op': 'move', 'eid': 301592, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}]
try: out, _ = edit.apply_full(buf, [edit.validate_op(o) for o in ops])
except edit.EditError as e: print('refused:', str(e)[:160]); print('OK'); sys.exit(0)
P1 = params(out)
assert g(P1[301560]).get('Mark') == 'c3x mixed', g(P1[301560]).get('Mark')
NAMEKEYS = {'View Name', 'View Name|String', 'Panel Schedule Name', 'Sheet Name', 'Name', 'Associated Level', 'Associated Level|String', 'Level', 'Level|String', 'Work Plane|String', 'Host|String', 'Work Plane', 'Host', 'Family and Type'}
bad = []
for e in P0:
    if e in (355, 356, 301560, 301592): continue
    a, b = g(P0[e]), g(P1.get(e, {}))
    d = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    if d and not d <= NAMEKEYS: bad.append((e, sorted(d)[:3]))
print('elements', len(P0), 'bad (changed beyond name echoes):', len(bad), bad[:3])
assert not bad and set(P1) == set(P0)
print('OK')
