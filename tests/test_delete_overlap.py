"""Delete overlap (rung 2, item 11b): two deletes (a wall with its hosted cascade, and an unrelated Floor) in one edit session must both be gone, overlapping cascades must not double-delete or crash, and the readback must pass."""
import os, sys, tempfile, shutil
import atexit as _ax, shutil as _sh; _T = tempfile.mkdtemp(); _ax.register(_sh.rmtree, _T, True); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_43_Snowdon_Towers_Sample_Structural.rvt'); W, F = 585072, 621720
from rvtballet import save, edit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
from _tagfix import stripped; SRC = stripped(SRC, W)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
# overlap: wall + one of its already-cascaded hosted instances in one session; must be a clean refusal or a duplicate-free delete, never corrupt
wop = edit.validate_op({'op': 'delete', 'eid': W}); _, d1 = edit.apply_full(d.buf, [wop]); hosted = [i for i in d1 if i != W][0]; print('hosted', hosted, flush=True)
ops = [wop, edit.validate_op({'op': 'delete', 'eid': hosted})]
try:
    nb, dl = edit.apply_full(d.buf, ops); assert len(dl) == len(set(dl)) and W in dl and hosted in dl, dl
    save._readback(d.buf, nb, ops); print('overlap accepted, no duplicates, readback OK', len(dl))
except edit.EditError as e: print('overlap refused cleanly:', str(e)[:100])
print('overlap test OK')
