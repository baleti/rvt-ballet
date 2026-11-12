"""Delete regression (rung 2, queue item 11): two deletes (a wall with its hosted cascade, and an unrelated Floor) in one edit session must both be gone, overlapping cascades must not double-delete or crash, and the readback must pass."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_43_Snowdon_Towers_Sample_Structural.rvt'); W, F = 585072, 621720
from rvtballet import save, edit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
from _tagfix import stripped; SRC = stripped(SRC, W)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
ops = [edit.validate_op({'op': 'delete', 'eid': i}) for i in (W, F)]
import time; t0 = time.time(); print('start', flush=True)
nb, deleted = edit.apply_full(d.buf, ops); print('apply_full %.0fs' % (time.time() - t0), flush=True)
assert W in deleted and F in deleted and len(deleted) == len(set(deleted)) and len(deleted) > 2, deleted
save._readback(d.buf, nb, ops)
print('two deletes in one save OK', len(deleted))
# duplicate / overlapping: deleting a hosted instance already cascaded by the wall must fail cleanly or be a no-op, never corrupt
hosted = [i for i in deleted if i not in (W, F)][0]
try:
    nb2, del2 = edit.apply_full(d.buf, ops + [edit.validate_op({'op': 'delete', 'eid': hosted})]); print('overlap accepted', len(del2)); assert len(del2) == len(set(del2)) and len(del2) == len(deleted); save._readback(d.buf, nb2, ops + [edit.validate_op({'op': 'delete', 'eid': hosted})])
except edit.EditError as e: print('overlap refused cleanly:', str(e)[:80])
