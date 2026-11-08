"""SAVE! in place on a source that is a symlink: the link must stay a link and the REAL file must receive the save (not replaced-link-with-stale-target).
Needs the savegate fix (resolve realpath before the atomic replace); until then this reports FAIL."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.makedirs(_T + '/real')
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
json_gate = _T + '/gate.json'; open(json_gate, 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = json_gate
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
real = _T + '/real/r.rte'; shutil.copy(S, real); link = _T + '/link.rte'; os.symlink(real, link)
ss = save.SaveSessions(); d = ss.doc('m', link)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
h0 = sha(real)
try: save.save_overwrite(ss, 'm', link, new_bytes=nb, manifest={'modified': ['el:301595']})
except Exception as e: print('refused (acceptable, nothing written):', type(e).__name__); assert sha(real) == h0 and os.path.islink(link); sys.exit(0)
assert os.path.islink(link), 'FAIL: symlink replaced by a regular file'
assert sha(real) != h0 and sha(real) == hashlib.sha256(nb).hexdigest(), 'FAIL: real target not updated'
print('save symlink source OK')
