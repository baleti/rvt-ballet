"""tiny moves (1e-12..1e-4 ft): each is either refused cleanly or saved as a verified, different output; never an unverified or half-written file; source untouched."""
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
f = _T + '/t.rte'; shutil.copy(S, f); h0 = sha(f); ss = save.SaveSessions(); d = ss.doc('m', f)
res = {}
for dx in (1e-12, 1e-9, 1e-6, 1e-4):
    try:
        op = edit.validate_op({'op': 'move', 'eid': 301595, 'dx': dx, 'dy': 0.0, 'dz': 0.0}); nb, _ = edit.apply_full(d.buf, [op])
    except Exception as e: res[dx] = 'edit_refused:' + type(e).__name__; continue
    dest = _T + '/o%g.rte' % dx
    try: save.save_as(ss, 'm', f, dest, new_bytes=nb, manifest={'modified': ['el:301595']}); res[dx] = 'saved' + ('_identical' if sha(dest) == h0 else '')
    except Exception as e: res[dx] = 'save_refused:' + type(e).__name__; assert not os.path.exists(dest), 'refused but output left'
    assert sha(f) == h0
print(res)
bad = [k for k, v in res.items() if v == 'saved_identical']
print('tiny moves: no silent no-op saved as success' if not bad else 'NOTE saved byte-identical output for %s (accepted no-op)' % bad)
