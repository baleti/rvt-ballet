"""SAVE! in place of a source opened through a symlinked DIRECTORY: the real file gets the edited bytes, the symlink stays a symlink, backup has the original, no stray files in the real dir."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(_T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
real = _T + '/real'; os.makedirs(real); link = _T + '/link'; os.symlink(real, link)
a_real = real + '/m.rte'; shutil.copy(S, a_real); h0 = sha(a_real); a = link + '/m.rte'
ss = save.SaveSessions(); d = ss.doc('m', a)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
r = save.save_overwrite(ss, 'm', a, new_bytes=nb, manifest={'modified': ['el:301595']})
assert os.path.islink(link), 'directory symlink was replaced'
assert sha(a_real) == hashlib.sha256(nb).hexdigest(), 'real file does not hold the edited bytes'
left = [f for f in os.listdir(real) if f not in ('m.rte', '.savegate')]
assert not left, 'stray files: %r' % left
bk = [os.path.join(r0, f) for r0, _, fs in os.walk(real) for f in fs if f != 'm.rte']
assert any(sha(b) == h0 for b in bk), 'no backup with original bytes found under the real dir'
print('symlinked directory in-place save OK')
