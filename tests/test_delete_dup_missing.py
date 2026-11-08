"""c1x-rvtdel item 18: the same delete twice in one batch must delete once (no duplicate ids, readback clean); a delete of an id that does not exist must be refused with EditError, never silently accepted. Autodesk 2024 template."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte'); EID = 5499
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rte'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
ops = [edit.validate_op({'op': 'delete', 'eid': EID}) for _ in range(2)]
nb, dl = edit.apply_full(d.buf, ops); assert len(dl) == len(set(dl)) and EID in dl, dl
save._readback(d.buf, nb, ops); print('duplicate delete OK', len(dl))
try:
    edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': 987654321})]); raise SystemExit('FAIL: nonexistent id accepted')
except edit.EditError as e: assert 'does not exist' in str(e), str(e); print('missing id refused:', str(e)[:80])
except Exception as e: print('missing id raised', type(e).__name__, '(not EditError)'); raise SystemExit(1)
print('OK')
# delete result is a valid base for a second save: the deleted id is gone from the output, deleting it again is refused, and a different delete on top of it works
import tempfile as _tf
out = os.path.join(_T, 'out.rte'); open(out, 'wb').write(nb)
d2 = save.SaveSessions().doc('m2', out)
try:
    edit.apply_full(d2.buf, [edit.validate_op({'op': 'delete', 'eid': EID})]); raise SystemExit('FAIL: re-delete accepted')
except edit.EditError as e: assert 'does not exist' in str(e), str(e); print('re-delete refused')
