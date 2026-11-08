"""In-place SAVE! and RESTORE of sources with awkward names: non-ASCII + spaces + uppercase extension, and a very long directory path. Original replaced correctly, backup holds the original, restore returns it, no temp/lock files left."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
base = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = base + '/j'; os.environ['SAVEGATE_CACHE'] = base + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = base + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(base + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = base + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
cases = [os.path.join(base, 'ünï cödé 日本語 dir', 'Proyecto ñ  (v2) – final.RVT'), os.path.join(base, *['d' * 40] * 5, 'long.rvt')]
for n, p in enumerate(cases):
    os.makedirs(os.path.dirname(p)); shutil.copy(S, p); h0 = sha(p)
    ss = save.SaveSessions(); d = ss.doc('m%d' % n, p)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    save.save_overwrite(ss, 'm%d' % n, p, new_bytes=nb, manifest={'modified': ['el:301595']})
    assert sha(p) == hashlib.sha256(nb).hexdigest() != h0, ('not saved', p[-20:])
    bl = save.backups(p); assert bl and sha(bl[0]['path']) == h0, 'backup missing/wrong'
    save.restore_backup(ss, 'm%d' % n, p, 0); assert sha(p) == h0, 'restore failed'
    left = [f for f in os.listdir(os.path.dirname(p)) if f.endswith(('.tmp', '.part', '.sgtmp', '.lock'))]; assert not left, left
print('in-place save/restore with awkward names OK (%d cases)' % len(cases))
