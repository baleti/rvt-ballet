"""c6x-rvtmatrix item 8: two ops on the SAME element in one edit (set_num Base Offset + move) on the synthetic 2024 cols2 FamilyInstance 301595: either honestly refused, or both applied: Base Offset read back, and no element outside 301595 changed in params."""
import os, sys, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import rvt_params
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
P0 = rvt_params.params(S); E = 301595; base = g(P0[E]).get('Base Offset')
def params(b):
    d = tempfile.mkdtemp(); p = d + '/x.rte'; open(p, 'wb').write(b); return rvt_params.params(p)
ops = [{'op': 'set_num', 'eid': E, 'param': 'Base Offset', 'kind': 'Double', 'value': 0.25}, {'op': 'move', 'eid': E, 'dx': 0.5, 'dy': 0.0}]
try: out, _ = edit.apply_full(buf, [edit.validate_op(o) for o in ops])
except edit.EditError as e: print('refused:', str(e)[:120]); print('OK'); sys.exit(0)
P1 = params(out); got = g(P1[E]).get('Base Offset'); print('base offset', base, '->', got)
bad = [e for e in P0 if e not in [301595] and (e not in P1 or g(P0[e]) != g(P1[e]))]
print('changed outside element:', len(bad)); assert got is not None and abs(got - 0.25) < 1e-6 and not bad, (got, bad[:5])
print('OK')
