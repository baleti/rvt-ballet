"""Item 201: the BACKUP file is damaged (one byte flipped, and separately truncated) after a successful save; RESTORE must refuse and leave the current file untouched (never write a damaged backup over the file). Previous: Item 199 (stale save after RESTORE): model B loaded, A saves, the file is restored from the backup (original bytes again), then B saves: B must be refused or at least not corrupt; here the bytes equal B's base again, so what is asserted is the outcome class. Original docstring: Item 198: the same file is loaded as two models (A, B). A saves a move in place; B (stale: loaded before A's save) then saves a different move. B must be refused (Conflict), A's result must stay byte-identical, no leftovers. Synthetic 2024 .rte."""
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
d1 = ss.doc('A', p); n1, _ = edit.apply_full(d1.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'A', p, new_bytes=n1, manifest={'modified': ['el:301595']}); h1 = sha(p)
bk = [b for b in save.backups(p) if sha(b['path']) == h0]; assert bk; bp = bk[0]['path']; good = open(bp, 'rb').read()
for label, dmg in (('bitflip', lambda b: b[:len(b)//2] + bytes([b[len(b)//2] ^ 0x40]) + b[len(b)//2+1:]), ('truncated', lambda b: b[:len(b)-5000])):
    open(bp, 'wb').write(dmg(good))
    n = next(b['n'] for b in save.backups(p) if b['path'] == bp)
    try: save.restore_backup(ss, 'R', p, n); out = 'RESTORED'
    except Exception as e: out = 'refused %s: %s' % (type(e).__name__, str(e)[:90])
    print(label, out, '| file still the saved version:', sha(p) == h1)
    assert out != 'RESTORED' and sha(p) == h1, label + ': damaged backup written over the file'
    open(bp, 'wb').write(good)
assert not [f for f in os.listdir(T) if f.endswith('.part') or 'sgtmp' in f]
print('OK')
