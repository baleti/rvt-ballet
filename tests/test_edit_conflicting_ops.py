"""c1x-rvtsave 210: conflicting ops in ONE edit batch (delete+move, move+delete, delete+delete, delete+set_string on the same element) must be refused or collapse to a defined result; never a half-applied file. Synthetic 2024 .rte."""
import os, sys, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
from rvtballet import edit
import rvt_params
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); E = 301595
def params(b):
    d = tempfile.mkdtemp(); p = os.path.join(d, 'x.rte'); open(p, 'wb').write(b); return rvt_params.params(p)
P0 = params(buf); g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
M = {'op': 'move', 'eid': E, 'dx': 1.0}; D = {'op': 'delete', 'eid': E}; C = {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 'x'}
res = {}
for name, ops in (('delete+move', [D, M]), ('move+delete', [M, D]), ('delete+delete', [D, D]), ('delete+set_string', [D, C]), ('set_string+delete', [C, D])):
    try: out, _ = edit.apply_full(buf, [edit.validate_op(dict(o)) for o in ops])
    except edit.EditError as e: res[name] = 'refused'; continue
    P1 = params(out)
    diff = [e for e in P0 if e in P1 and g(P0[e]) != g(P1[e])]; gone = [e for e in P0 if e not in P1]
    assert set(diff + gone) <= {E}, (name, 'other elements changed', diff, gone)
    res[name] = 'applied: eid %s' % ('deleted' if E in gone else 'edited' if E in diff else 'unchanged')
print(res); print('OK')
