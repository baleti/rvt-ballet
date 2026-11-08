"""Item 190: in-place SAVE of a real edit (move) through a symlink path: the link must survive and the TARGET must hold the edited bytes (not a stale copy)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ss = save.SaveSessions()
real = T + '/real.rte'; shutil.copy(S, real); lnk = T + '/lnk.rte'; os.symlink(real, lnk); h0 = sha(real)
dd = ss.doc('m', lnk)
nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', lnk, new_bytes=nb, manifest={'modified': ['el:301595']})
nh = hashlib.sha256(nb).hexdigest()
print('symlink kept:', os.path.islink(lnk), '| target has edit:', sha(real) == nh)
assert os.path.islink(lnk) and os.path.realpath(lnk) == os.path.realpath(real), 'symlink replaced by a regular file'
assert sha(real) == nh and sha(lnk) == nh, 'edit not in the target'
assert h0 != nh
print('OK')
