"""c3x-rvtdel item 22: deleting a type/style that other elements reference must be refused (it used to be accepted, deleting 1 id and leaving 12 dangling dimension type refs on Structural 2024 DimensionStyle 908160)."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt'); EID = 908160
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': EID})]); raise SystemExit('FAIL: in-use DimensionStyle delete accepted')
except edit.EditError as e: assert 'still referenced' in str(e), str(e); print('in-use style refused:', str(e)[:90])
print('OK')
