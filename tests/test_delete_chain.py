"""Delete chain (rung 2): delete wall 585072 (+cascade), write the output, re-open IT and delete floor 621720 from it; the second readback must pass against the first output (a delete output must re-parse and edit like an original). Structural 2024 sample only."""
import os, sys, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_43_Snowdon_Towers_Sample_Structural.rvt'); W, F = 585072, 621720
from rvtballet import save, edit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
from _tagfix import stripped; SRC = stripped(SRC, W)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src)
d = save.SaveSessions().doc('m', src)
op = edit.validate_op({'op': 'delete', 'eid': W}); nb, del1 = edit.apply_full(d.buf, [op]); save._readback(d.buf, nb, [op])
o1 = os.path.join(_T, 'o1.rvt'); open(o1, 'wb').write(nb)
d2 = save.SaveSessions().doc('m2', o1)
op2 = edit.validate_op({'op': 'delete', 'eid': F}); nb2, del2 = edit.apply_full(d2.buf, [op2]); save._readback(d2.buf, nb2, [op2])
assert F in del2 and not set(del1) & set(del2) and nb2 != nb
print('delete chain OK: %d + %d ids' % (len(del1), len(del2)))
