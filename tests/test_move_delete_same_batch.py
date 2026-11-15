"""c1x-rvtmove: move+delete of the same element in ONE batch, and move of an already deleted id, must never yield an accepted file that is inconsistent: either EditError or readback-clean result with the id gone. Autodesk 2024 template."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte'); EID = 5499
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rte'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
for order, kind in ((0, 'move'), (1, 'move'), (0, 'rotate'), (1, 'rotate')):
    mv = {'op': 'move', 'eid': EID, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0} if kind == 'move' else {'op': 'rotate', 'eid': EID, 'deg': 30.0}
    ops = [edit.validate_op(mv), edit.validate_op({'op': 'delete', 'eid': EID})]
    if order: ops.reverse()
    try:
        nb, dl = edit.apply_full(d.buf, ops)
    except edit.EditError as e: print(kind, 'order', order, 'refused:', str(e)[:90]); continue
    assert EID in dl, dl
    try: save._readback(d.buf, nb, ops)
    except Exception as e: print(kind, 'order', order, 'readback refused:', type(e).__name__, str(e)[:90]); continue
    print(kind, 'order', order, 'accepted, id deleted, readback clean')
print('OK')
