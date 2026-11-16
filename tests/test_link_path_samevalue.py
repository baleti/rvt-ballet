"""c3x-rvtlink: set_link_path with the link's current path is refused ('nothing to change'), not a whole-partition rewrite. Local Revit-made 2024 file (skipped if absent)."""
import os, sys
SEED = os.path.expanduser('~/c5x-link/fl/la_a2.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
from rvtballet import edit
buf = open(SEED, 'rb').read()
try: edit.apply(buf, [{'op': 'set_link_path', 'eid': 1542984, 'value': 'C:\\wl\\la_tgt.rvt'}])
except edit.EditError as e: assert 'nothing to change' in str(e), str(e); print('OK same-value path refused'); sys.exit(0)
raise SystemExit('ACCEPTED a same-value path edit')
