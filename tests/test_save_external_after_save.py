"""AFTER a first edited SAVE! in the same session, the file is modified behind the viewer's back with the SAME size and the SAME mtime (content changed only): in-place SAVE! must still notice (Conflict) and leave that other program's version untouched."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
import json; json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.environ.get('SRC') or os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = T + '/m.rte'; shutil.copy(S, p)
ss = save.SaveSessions(); d = ss.doc('m', p)
if os.environ.get('SRC'):
    import rvt_params; g = lambda x: x.get('params', x) if isinstance(x, dict) else {}
    E1, E2 = [e for e, dd in rvt_params.params(S).items() if g(dd).get('Comments') == ''][:2]
    op = lambda e, v: {'op': 'set_string', 'eid': e, 'param': 'Comments', 'value': v}
else:
    E1, E2 = 301595, 301596; op = lambda e, v: {'op': 'move', 'eid': e, 'dx': 1.0}
nb, _ = edit.apply_full(d.buf, [edit.validate_op(op(E1, 'a'))])
save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % E1]}); assert sha(p) != sha(S), 'first save did not change the file'
nb2, _ = edit.apply_full(nb, [edit.validate_op(op(E2, 'b'))])
st = os.stat(p); b = bytearray(open(p, 'rb').read()); b[-1] ^= 0xFF; open(p, 'wb').write(bytes(b)); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
assert os.stat(p).st_size == st.st_size and os.stat(p).st_mtime_ns == st.st_mtime_ns; h1 = sha(p)
try: save.save_overwrite(ss, 'm', p, new_bytes=nb2, manifest={'modified': ['el:%d' % E2]}); raise SystemExit('FAIL: second save overwrote a file changed behind its back after the first save')
except SystemExit: raise
except Exception as e: err = type(e).__name__
assert sha(p) == h1, "the other program's version was modified"
left = [f for f in os.listdir(T) if f.endswith(('.tmp', '.part', '.sgtmp'))]; assert not left, left
print('second save after external same-size same-mtime change refused:', err)
