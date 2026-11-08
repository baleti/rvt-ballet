"""c4x-rvtmatrix: move and rotate of classes without a Revit-verified implementation (Viewport, Viewer, DBViewPlan, sheet) are refused, never applied. Synthetic 2024 vports1 scene."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_vports1.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read()
for eid in (301604, 301609, 301610, 301611):   # Viewport, DBViewDrafting, Viewer, Viewport
    for op in ({'op': 'move', 'eid': eid, 'dx': 0.5}, {'op': 'rotate', 'eid': eid, 'deg': 10.0}):
        try: edit.apply_full(buf, [edit.validate_op(dict(op))])
        except edit.EditError: continue
        raise AssertionError('%s of unverified class element %d was applied' % (op['op'], eid))
print('OK')
