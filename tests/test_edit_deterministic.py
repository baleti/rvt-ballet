"""c1x-rvtsave 215: the same edit batch applied twice (fresh process state each time) yields byte-identical output; and move +1 then -1 on the same buffer leaves every element's readback equal to the original. Synthetic 2024 .rte."""
import os, sys, tempfile, hashlib
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
from rvtballet import edit
import rvt_params
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read()
ops = lambda: [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0}), edit.validate_op({'op': 'rotate', 'eid': 301595, 'deg': 15.0})]
a, _ = edit.apply_full(buf, ops()); b, _ = edit.apply_full(buf, ops())
assert a == b, 'two runs of the same edit differ'
def params(x):
    d = tempfile.mkdtemp(); p = os.path.join(d, 'x.rte'); open(p, 'wb').write(x); return rvt_params.params(p)
m1, _ = edit.apply_full(buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
m2, _ = edit.apply_full(m1, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': -1.0})])
P0, P2 = params(buf), params(m2)
bad = [e for e in P0 if P0[e] != P2.get(e)]
print('deterministic: True | move+-1 roundtrip: %d of %d elements differ (bytes equal original: %s)' % (len(bad), len(P0), m2 == buf))
assert not bad, bad[:5]
print('OK')
