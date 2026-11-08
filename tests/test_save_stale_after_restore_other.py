"""Item 200 (restore to a DIFFERENT older version): C loaded at the original; two saves v1, v2 follow; file restored to v1 (not C's base); C saves: must be REFUSED (Conflict), file stays v1. Previous: Item 199 (stale save after RESTORE): model B loaded, A saves, the file is restored from the backup (original bytes again), then B saves: B must be refused or at least not corrupt; here the bytes equal B's base again, so what is asserted is the outcome class. Original docstring: Item 198: the same file is loaded as two models (A, B). A saves a move in place; B (stale: loaded before A's save) then saves a different move. B must be refused (Conflict), A's result must stay byte-identical, no leftovers. Synthetic 2024 .rte."""
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
dc = ss.doc('C', p)
nc, _ = edit.apply_full(dc.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 9.0})])
d1 = ss.doc('A1', p); n1, _ = edit.apply_full(d1.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'A1', p, new_bytes=n1, manifest={'modified': ['el:301595']}); h1 = sha(p)
d2 = ss.doc('A2', p); n2, _ = edit.apply_full(d2.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 2.0})])
save.save_overwrite(ss, 'A2', p, new_bytes=n2, manifest={'modified': ['el:301595']}); h2 = sha(p); assert len({h0, h1, h2}) == 3
n = next(b['n'] for b in save.backups(p) if sha(b['path']) == h1); save.restore_backup(ss, 'R', p, n); assert sha(p) == h1
try: save.save_overwrite(ss, 'C', p, new_bytes=nc, manifest={'modified': ['el:301595']}); out = 'ACCEPTED'
except Exception as e: out = 'refused %s: %s' % (type(e).__name__, str(e)[:90])
print(out); assert out != 'ACCEPTED' and sha(p) == h1, 'stale model overwrote the restored version'
assert not [f for f in os.listdir(T) if f.endswith('.part') or 'sgtmp' in f]
print('OK')
