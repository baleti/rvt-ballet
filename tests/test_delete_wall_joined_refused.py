"""Delete regression (rung 2, c1x-rvtdel item 119): Revit-made Delete of Site 2024 wall 1139388 rewrote the joined neighbour wall 1139389 (join entry cleared, geometry regenerated). Our delete left the join entry naming the removed wall, so a joined wall must be refused (nothing written). Autodesk sample only."""
import os, sys, tempfile, shutil
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit as _ax; _T = tempfile.mkdtemp(); _ax.register(shutil.rmtree, _T, True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_47_Snowdon_Towers_Sample_Site.rvt'); W = int(os.environ.get('W', 1139388)); WORD = 'joined' if W == 1139388 else 'still named'
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src)
d = save.SaveSessions().doc('m', src)
op = edit.validate_op({'op': 'delete', 'eid': W})
try: edit.apply_full(d.buf, [op])
except edit.EditError as e: assert WORD in str(e), e; print('refused OK:', str(e)[:90])
else: raise SystemExit('FAIL: joined wall delete accepted')
