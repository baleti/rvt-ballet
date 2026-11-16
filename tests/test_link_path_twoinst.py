"""c3x-rvtlink: set_link_path on a link TYPE with 2 instances edits only the type record (Partitions/24); instances untouched.
Local Revit-made 2024 file (skipped if absent)."""
import os, sys, tempfile
SEED = os.path.expanduser('~/c5x-link/fl/la_a2.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
import rvtedit
from rvtballet import edit
out = os.path.join(tempfile.mkdtemp(), 'o.rvt')
edit._apply_rvtedit(SEED, out, [{'op': 'set_link_path', 'eid': 1542984, 'value': 'Renamed Target.rvt'}])
e = rvtedit.Edit(out)
log = e.g.e.trace(1542984)[3]
cur = [str(l[4]) for l in log if l[1] == 'ModelPath.m_path']
assert cur and cur[0] == 'Renamed Target.rvt', cur
for inst in (1542985, 1542987):
    assert e.g.e.trace(inst), inst
print('OK type edited, both instances still present')
