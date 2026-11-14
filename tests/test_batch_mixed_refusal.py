"""c7x-rvtmove item 88: a batch with one valid move and one refused op (move below witness resolution, or nonexistent eid) must be refused as a whole, never half-applied (the valid move must not be saved alone). cols2 synthetic scene (local)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit
if not os.path.exists(F): print('skip'); sys.exit(0)
buf = open(F, 'rb').read(); A, B = 301592, 301595; bad = 0
def mk(e, d): return dict(op='move', eid=e, dx=d, dy=0.0, dz=0.0)
def val(o):
    try: return edit.validate_op(o)
    except edit.EditError: return None
for lab, ops in (('good+tiny', [mk(A, 1.0), mk(B, 1e-9)]), ('good+missing eid', [mk(A, 1.0), mk(999999991, 1.0)]), ('tiny+good', [mk(B, 1e-9), mk(A, 1.0)])):
    vs = [val(o) for o in ops]
    try:
        if None in vs: raise edit.EditError('validate refused')
        edit.apply_full(buf, vs); r = 'APPLIED'
    except edit.EditError as x: r = 'refused'
    print(lab, r, '' if r == 'refused' else 'FAIL'); bad += r != 'refused'
sys.exit(1 if bad else 0)
