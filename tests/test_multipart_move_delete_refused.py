"""c5x-rvtlink: move and delete of an element with records in several partitions are refused (2026 Electrical sample, link type 1362427 in Partitions/39 and 41; local ~/c5x-link/y2526b/e26_seed.rvt, skipped if absent)."""
import os, sys
SRC = os.path.expanduser('~/c5x-link/y2526b/e26_seed.rvt')
if not os.path.exists(SRC): print('SKIP: no seed'); sys.exit(0)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
from rvtballet import edit
buf = open(SRC, 'rb').read()
for op in ({'op': 'move', 'eid': 1362427, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}, {'op': 'delete', 'eid': 1362427}):
    try: edit.apply_full(buf, [edit.validate_op(op)]); raise SystemExit('accepted: %s' % op['op'])
    except edit.EditError as e: assert 'several partitions' in str(e), (op['op'], str(e)[:200])
print('OK multi-partition move/delete refused')
