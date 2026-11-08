"""in-place SAVE! (save_overwrite, gate forced open on a private copy) of move +2 ft AND rotate 30 of ONE instance (301595, cols2 scene): accepted, the file changes, then restore_backup returns the original byte-exact."""
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
f = _T + '/w.rte'; shutil.copy(S, f); h0 = sha(f); ss = save.SaveSessions(); d = ss.doc('m', f)
ops = [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 2.0, 'dy': 0.0, 'dz': 0.0}), edit.validate_op({'op': 'rotate', 'eid': 301595, 'deg': 30})]
nb, _ = edit.apply_full(d.buf, ops)
r = save.save_overwrite(ss, 'm', f, new_bytes=nb, manifest={'modified': ['el:301595']})
assert sha(f) != h0 and open(f, 'rb').read() == nb, 'accepted but the file is not the verified output'
print('in-place move+rotate saved:', str(r)[:100])
save.restore_backup(ss, 'm', f)
assert sha(f) == h0, 'restore did not return the original'
assert not [x for x in os.listdir(_T) if '.tmp' in x or '.part' in x], 'temp left'
print('in-place move+rotate save + restore byte-exact OK')
