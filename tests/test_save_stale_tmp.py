"""(stale temp debris) Source mtime in 1970 / year 2100 / now+0: honest in-place SAVE! must succeed, backup holds the original bytes and RESTORE returns it. Was: The file is modified behind the viewer's back with the SAME size and the SAME mtime (content changed only): in-place SAVE! must still notice (Conflict) and leave that other program's version untouched."""
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
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ss = save.SaveSessions()
p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p); d = ss.doc('m', p)
# debris of a killed earlier save/restore: same-name temps, one garbage, one a truncated copy of the source
open(T + '/.m.rte.dead01.aaaaaaaa.sgtmp', 'wb').write(b'garbage' * 100000)
open(T + '/.m.rte.dead02.bbbbbbbb.sgtmp', 'wb').write(open(p, 'rb').read()[:2 ** 20])
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
r = save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
assert sha(p) == hashlib.sha256(nb).hexdigest(), 'saved file is not the new bytes'
save.restore_backup(ss, 'm', p, 0)
assert sha(p) == h0, 'restore did not return the original'
print('stale temps beside the source: save + restore OK; temps left:', sorted(x for x in os.listdir(T) if x.endswith('.sgtmp')))
