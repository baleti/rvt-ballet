"""c1x-rvtsave 217: in-place SAVE of a real edit with unusual names: upper-case extension, no extension, double extension. Each must save in place (edit present) or refuse cleanly leaving the file byte-identical; never a stray result."""
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
for i, name in enumerate(('UP.RTE', 'noext', 'a.rte.rte', 'x.RvT')):
    p = T + '/' + name; shutil.copy(S, p); h0 = sha(p)
    try:
        dd = ss.doc('m%d' % i, p)
        nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
        save.save_overwrite(ss, 'm%d' % i, p, new_bytes=nb, manifest={'modified': ['el:301595']})
        ok = sha(p) == hashlib.sha256(nb).hexdigest() and sha(p) != h0
        print(name, 'saved in place' if ok else 'SAVED WRONG'); assert ok, name
    except Exception as e:
        print(name, 'refused:', type(e).__name__, str(e)[:100]); assert sha(p) == h0, name + ' damaged on refusal'
left = [f for f in os.listdir(T) if f.endswith('.sgtmp')]; assert not left, left
print('OK')
