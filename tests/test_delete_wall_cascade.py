"""Delete regression (rung 2): deleting a wall that hosts doors/windows must take the hosted instances with it (Revit's own cascade, VM-measured 10 hosted FamilyInstances on Snowdon Structural 2024 wall 585072), never leave them dangling. The result must not contain the wall nor any deleted id, and every non-deleted element must be unchanged."""
import os, sys, tempfile, shutil
import atexit as _ax, shutil as _sh; _T = tempfile.mkdtemp(); _ax.register(_sh.rmtree, _T, True); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_43_Snowdon_Towers_Sample_Structural.rvt'); W = 585072
os.environ['RVTBALLET_DELETE_WALL_JOINED'] = '1'      # c1x-rvtdel item 119: this test checks the hosted-instance cascade id set only; wall 585072 is joined to 3 walls and the default gate now refuses that
from rvtballet import save, edit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
from _tagfix import stripped; SRC = stripped(SRC, W)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src)
d = save.SaveSessions().doc('m', src)
op = edit.validate_op({'op': 'delete', 'eid': W})
nb, deleted = edit.apply_full(d.buf, [op])
assert nb != d.buf and W in deleted and len(deleted) > 1, 'no cascade: %r' % (deleted,)
print('deleted', len(deleted), 'ids incl. wall')
save._readback(d.buf, nb, [op])      # every deleted id absent, nothing else changed
print('wall cascade delete OK')
