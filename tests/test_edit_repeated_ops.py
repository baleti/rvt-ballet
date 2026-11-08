"""c1x-rvtsave 216: the SAME op repeated on one element in one batch (set_string twice, move twice, move+rotate): refused or a defined result (last wins / sum), never other elements changed. Synthetic 2024 .rte."""
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
C = lambda v: {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': v}
M = lambda d: {'op': 'move', 'eid': E, 'dx': d}
res = {}
for name, ops in (('set2', [C('a'), C('b')]), ('move2', [M(1.0), M(2.0)]), ('move+set', [M(1.0), C('z')])):
    try: out, _ = edit.apply_full(buf, [edit.validate_op(dict(o)) for o in ops])
    except edit.EditError: res[name] = 'refused'; continue
    P1 = params(out)
    bad = [e for e in P0 if e != E and (e not in P1 or g(P0[e]) != g(P1[e]))]
    assert not bad, (name, 'other elements changed', bad)
    res[name] = 'applied, Comments=%r' % (g(P1[E]).get('Comments'),)
print(res); print('OK')
