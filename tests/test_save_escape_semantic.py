"""ESCAPE hunt (semantic): a VALID output (two real moves via the edit backend) handed to the gate with a manifest that under-declares
(only one of the two moved elements; nothing; the wrong element) must be refused, nothing written, source intact. The fully declared manifest passes."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, tempfile, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save, edit
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src)
A = 301595
ss = save.SaveSessions(); d = ss.doc('m', src)
rp = save._read_params(d.buf); B = next(i for i in sorted(rp) if i != A and edit.validate_op({'op': 'move', 'eid': i, 'dx': 1.0}) if True) if False else None
for i in sorted(rp):                      # a second element the backend accepts a move for
    if i == A: continue
    try: edit.validate_op({'op': 'move', 'eid': i, 'dx': 1.0}); nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': A, 'dx': 1.0}), edit.validate_op({'op': 'move', 'eid': i, 'dx': 1.0})]); B = i; break
    except Exception: continue
if B is None: print('skip: no second movable element'); sys.exit(0)
res = {}
for name, man, ok in (('declared_both', ['el:%d' % A, 'el:%d' % B], True), ('only_A', ['el:%d' % A], False), ('empty', [], False), ('wrong_C', ['el:%d' % A, 'el:%d' % (B + 1)], False)):
    dest = os.path.join(_T, 'o_%s.rvt' % name)
    try: save.save_as(ss, 'm', src, dest, new_bytes=nb, manifest={'modified': man}); acc = True
    except Exception as e: acc = False; res[name] = type(e).__name__
    if acc: res[name] = 'ACCEPTED'
    assert acc == ok, (name, res)
    if not acc: assert not os.path.exists(dest), name
    assert sha(src) == h0
print(res); print('save escape semantic OK (A=%d B=%d)' % (A, B))
