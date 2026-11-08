"""in-place SAVE! on files named UP.RVT, noext, a.rvt.bak, Mixed.Rte: verified save + byte-exact restore, or clean refusal with the file untouched; no temp debris."""
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
for name in ('UP.RVT', 'noext', 'a.rvt.bak', 'Mixed.Rte'):
    f = _T + '/' + name; shutil.copy(S, f); h0 = sha(f); ss = save.SaveSessions(); d = ss.doc('m', f)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})])
    try:
        save.save_overwrite(ss, 'm', f, new_bytes=nb, manifest={'modified': ['el:301595']})
        assert open(f, 'rb').read() == nb, name + ': accepted but file is not the verified output'
        save.restore_backup(ss, 'm', f); assert sha(f) == h0, name + ': restore not byte-exact'
        print(name, 'saved + restored OK')
    except AssertionError: raise
    except Exception as e:
        assert sha(f) == h0, name + ': refused but file changed'
        print(name, 'refused cleanly:', type(e).__name__)
assert not [x for x in os.listdir(_T) if '.tmp' in x or '.part' in x], 'temp left'
print('save under odd extensions OK')
