"""c3x-rvtdel item 24: deleting a view template (DBView.m_isTemplate=1) used by other views must be refused; it was accepted (2 ids) leaving dangling DBView.m_viewTemplateId in dozens of views (Structural 2024 template 780021)."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt'); EID = 780021
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 's.rvt'); shutil.copy(SRC, src); d = save.SaveSessions().doc('m', src)
try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': EID})]); raise SystemExit('FAIL: view template delete accepted')
except edit.EditError as e: assert 'view template' in str(e), str(e); print('view template refused')
print('OK')
