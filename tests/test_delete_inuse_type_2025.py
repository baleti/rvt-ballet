"""c1x-rvtdel item 30: deleting an in-use CompoundCeilingType (2025 Structural eid 359, 169 mentions) must be refused, never leave dangling refs."""
import os, sys, tempfile, shutil
import atexit as _ax, shutil as _sh; _T = tempfile.mkdtemp(); _ax.register(_sh.rmtree, _T, True); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvt-research/corpus/2025/49_Snowdon_Towers_Sample_Structural.rvt'); EID = 359
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
op = [edit.validate_op({'op': 'delete', 'eid': EID})]
# production gate: the 2025 year gate refuses first (2025 is not VM-verified for deletes)
try: edit.apply_full(d.buf, op); raise SystemExit('FAIL: in-use CompoundCeilingType delete accepted')
except edit.EditError as e: assert 'not VM-verified on Revit 2025' in str(e), str(e); print('production gate refused:', str(e)[:70])
# year gate bypassed (experiment mode): the in-use check itself must still refuse
os.environ['RVTBALLET_DELETE_ANY'] = '1'
try: edit.apply_full(d.buf, op); raise SystemExit('FAIL: in-use CompoundCeilingType delete accepted with DELETE_ANY')
except edit.EditError as e: assert 'still referenced' in str(e), str(e); print('in-use type refused:', str(e)[:90])
print('OK')
