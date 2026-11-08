"""Delete regression (rung 2, c1x-rvtdel item 48): deleting electrical panel 1403442 (Snowdon Electrical 2024) with the raw delete leaves 86 circuit-side FamilyInstances with Panel P506 -> None; the read-back must refuse (never accept a semantically changed output)."""
import os, sys, tempfile, shutil
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKUPS'] = _T + '/b'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_44_Snowdon_Towers_Sample_Electrical.rvt')
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
ops = [edit.validate_op({'op': 'delete', 'eid': 1403442})]
nb, deleted = edit.apply_full(d.buf, ops)
try: save._readback(d.buf, nb, ops)
except Exception as e:
    assert 'surviving' in str(e), str(e)[:200]; print('panel delete refused by readback OK:', str(e)[:90])
else: raise SystemExit('FAIL: panel delete accepted although 86 dependents lose their Panel')
