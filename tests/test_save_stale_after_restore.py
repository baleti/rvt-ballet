"""Item 199 (stale save after RESTORE): model B loaded, A saves, the file is restored from the backup (original bytes again), then B saves: B must be refused or at least not corrupt; here the bytes equal B's base again, so what is asserted is the outcome class. Original docstring: Item 198: the same file is loaded as two models (A, B). A saves a move in place; B (stale: loaded before A's save) then saves a different move. B must be refused (Conflict), A's result must stay byte-identical, no leftovers. Synthetic 2024 .rte."""
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
p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p)
da = ss.doc('A', p); db = ss.doc('B', p)
na, _ = edit.apply_full(da.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
nb, _ = edit.apply_full(db.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 5.0})])
save.save_overwrite(ss, 'A', p, new_bytes=na, manifest={'modified': ['el:301595']}); ha = sha(p); assert ha == hashlib.sha256(na).hexdigest() != h0
bk = save.backups(p); n = next(b['n'] for b in bk if sha(b['path']) == h0)
save.restore_backup(ss, 'R', p, n); assert sha(p) == h0
try: save.save_overwrite(ss, 'B', p, new_bytes=nb, manifest={'modified': ['el:301595']}); out = 'accepted'
except Exception as e: out = 'refused %s: %s' % (type(e).__name__, str(e)[:100])
print(out, '| file is B result:', sha(p) == hashlib.sha256(nb).hexdigest(), '| file is original:', sha(p) == h0)
assert sha(p) in (h0, hashlib.sha256(nb).hexdigest()), 'file is neither the original nor B result'
assert not [f for f in os.listdir(T) if f.endswith('.part') or 'sgtmp' in f]
print('OK')
