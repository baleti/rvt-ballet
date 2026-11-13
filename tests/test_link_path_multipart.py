"""c5x-rvtlink: set_link_path refuses a link type with records in several partitions (Revit 2026 VM 2026-11-13: edit in Partitions/39 was ignored, Revit read 41).
Autodesk Snowdon Electrical 2026 sample (local ~/c5x-link/y2526b/e26_seed.rvt, skipped if absent): link 1362427 refused; single-partition 2024 link still accepted."""
import os, sys
SEED = os.path.expanduser('~/c5x-link/y2526b/e26_seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_LINKPATH_ANY_YEAR'] = '1'
import rvtedit
from rvtballet import edit
try: edit._set_link_path(rvtedit.Edit(SEED), {'eid': 1362427, 'value': 'Moved_e26.rvt'}); raise SystemExit('multi-partition link accepted')
except edit.EditError as e: assert 'several partitions' in str(e), e
print('OK multi-partition link path refused')
