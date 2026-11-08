"""(clock skew) Source mtime in 1970 / year 2100 / now+0: honest in-place SAVE! must succeed, backup holds the original bytes and RESTORE returns it. Was: The file is modified behind the viewer's back with the SAME size and the SAME mtime (content changed only): in-place SAVE! must still notice (Conflict) and leave that other program's version untouched."""
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
for tag, mt in (('epoch0', 0), ('future2100', 4102444800), ('pre1970', -86400 * 400)):
    p = T + '/m_%s.rte' % tag; shutil.copy(S, p); os.utime(p, (mt, mt)); h0 = sha(p)
    d = ss.doc('m' + tag, p)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    r = save.save_overwrite(ss, 'm' + tag, p, new_bytes=nb, manifest={'modified': ['el:301595']})
    assert sha(p) != h0, tag + ': file unchanged'
    bk = r.get('backup') if isinstance(r, dict) else None
    assert bk and sha(bk) == h0, tag + ': backup is not the original'
    save.restore_backup(ss, 'm' + tag, p, 0)
    assert sha(p) == h0, tag + ': restore did not return the original'
    print(tag, 'saved, backup == original, restore byte-identical, restored mtime %d' % os.stat(p).st_mtime)
print('clock-skew mtimes OK')
