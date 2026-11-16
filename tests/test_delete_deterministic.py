"""Delete determinism (rung 2): the same delete applied twice to the same bytes gives byte-identical output (no timestamps, ordering or uninitialised bytes leaking in). Structural 2024 floor 621720."""
import os, sys, tempfile, shutil, hashlib
import atexit as _ax, shutil as _sh; _T = tempfile.mkdtemp(); _ax.register(_sh.rmtree, _T, True); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_43_Snowdon_Towers_Sample_Structural.rvt'); F = 621720
from rvtballet import save, edit
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src)
d = save.SaveSessions().doc('m', src)
h = []
for _ in range(2):
    nb, dele = edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': F})]); h.append(hashlib.sha256(nb).hexdigest())
assert h[0] == h[1], h
print('delete deterministic OK', h[0][:12])
