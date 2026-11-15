"""c1x-rvtmove: move/rotate of an id that was deleted in the input file (output of a prior delete save) must be refused with EditError, never saved. Autodesk 2024 template."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte'); EID = 5499
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rte'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
nb, dl = edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': EID})]); assert EID in dl
out = os.path.join(_T, 'out.rte'); open(out, 'wb').write(nb); d2 = save.SaveSessions().doc('m2', out)
for mv in ({'op': 'move', 'eid': EID, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}, {'op': 'rotate', 'eid': EID, 'deg': 30.0}):
    try: edit.apply_full(d2.buf, [edit.validate_op(mv)]); raise SystemExit('FAIL: %s of deleted id accepted' % mv['op'])
    except edit.EditError as e: assert 'does not exist' in str(e), str(e); print(mv['op'], 'refused:', str(e)[:90])
print('OK')
