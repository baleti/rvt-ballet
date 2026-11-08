"""c1x-rvtsave 221: move by zero and rotate by 0/360 degrees are refused with EditError (no pointless rewrite). Synthetic 2024 .rte."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read()
for op in ({'op': 'move', 'eid': 301595, 'dx': 0.0, 'dy': 0.0, 'dz': 0.0}, {'op': 'rotate', 'eid': 301595, 'deg': 0.0}, {'op': 'rotate', 'eid': 301595, 'deg': 360.0}):
    try: edit.apply_full(buf, [edit.validate_op(op)])
    except edit.EditError: continue
    raise AssertionError(('not refused', op))
print('OK')
