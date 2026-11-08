"""c3x-rvtlink: set_link_path is Revit-verified on 2024 only; the edit layer refuses any other year (2020 Autodesk HYPERLOOP sample) and accepts 2024 (Snowdon HVAC). Offline, calls the edit function directly."""
import sys, os
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for l in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(l))
A = os.path.expanduser('~/c5x-link/w/hvac24.rvt'); B = os.path.expanduser('~/rvt-samples/2020_1_HYPERLOOP_MASTER.rvt')
if not (os.path.exists(A) and os.path.exists(B)): print('skip'); sys.exit()
import rvtedit
from rvtballet import edit
edit._set_link_path(rvtedit.Edit(A), {'eid': 1363937, 'value': 'C:\\a\\b.rvt'})
try: edit._set_link_path(rvtedit.Edit(B), {'eid': 1, 'value': 'C:\\a.rvt'}); raise SystemExit('2020 file was not refused')
except edit.EditError as e: assert 'only verified on Revit 2024' in str(e), e
print('OK')
