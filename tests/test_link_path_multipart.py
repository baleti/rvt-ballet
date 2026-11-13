"""NOTE: this passes with the old ed.g.bj read too, because apply_full selects PART per element so bj is already the right partition; the bug only showed for a direct rvtedit.Edit() on the default partition. Kept as an end-to-end 2025 regression, NOT a discriminating test of the buffer fix. c5x-rvtlink: set_link_path must read the old path from the element's own partition (2025 HVAC: link types live in Partitions/24, ed.g.bj is another partition: the old code read garbage). With the year guard overridden the edit through apply_full must succeed and change only that link type + its partition stream; the stored path must read back as the new value. Autodesk 2025 HVAC sample, skipped if absent."""
import os, sys, glob
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')] + [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab')]
c = glob.glob(os.path.expanduser('~/rvt-research/corpus/2025/*HVAC.rvt'))
if not c: print('SKIP: no 2025 sample'); sys.exit(0)
os.environ.update(RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_LINKPATH='1', RVTBALLET_LINKPATH_ANY_YEAR='1'); os.environ.pop('PART', None)
import tempfile, rvt_params
from rvtballet import edit
buf = open(c[0], 'rb').read()
out = bytes(edit.apply_full(buf, [edit.validate_op({'op': 'set_link_path', 'eid': 1363937, 'value': 'Moved_Target_25.rvt'})])[0])
assert out != buf and len(out) > 0
import rvtedit
with tempfile.NamedTemporaryFile(suffix='.rvt') as f:
    f.write(out); f.flush(); ed = rvtedit.Edit(f.name)
    got = [str(l[4]) for l in ed.g.e.trace(1363937)[3] if l[1] == 'ModelPath.m_path']
assert got == ['Moved_Target_25.rvt'], got
print('OK 2025 multi-partition link path edit')
