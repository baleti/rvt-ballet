"""regression: moving a RoomElem / Floor / Ceiling (no validated move implementation) is refused with EditError and nothing is written.
Autodesk finished_spec_example Ceiling .rte 2024 (local copy, keep dir); skipped when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/2024_finished_spec_example_Ceiling.rte')
from rvtballet import edit
if not os.path.exists(F): print('skip'); sys.exit(0)
buf = open(F, 'rb').read()
bad = 0
for name, eid in (('RoomElem', 301587), ('Floor', 301604), ('Ceiling', 301782)):
    for kind in ('move', 'rotate'):
        o = {'op': 'move', 'eid': eid, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0} if kind == 'move' else {'op': 'rotate', 'eid': eid, 'deg': 30.0}
        try:
            op = edit.validate_op(o); edit.apply_full(buf, [op]); print('FAIL accepted', name, kind); bad += 1
        except edit.EditError as e: print('refused', name, kind, str(e)[:80])
sys.exit(1 if bad else 0)
