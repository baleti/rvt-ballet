"""In-place SAVE! when writes fail part-way (RLIMIT_FSIZE below the file size, the same error path as a full disk): refused with a disk error, original byte-identical, no temp file, no partial backup left that RESTORE would take for a good one."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile, signal, resource
base = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = base + '/j'; os.environ['SAVEGATE_CACHE'] = base + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = base + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(base + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = base + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = base + '/m.rte'; shutil.copy(S, p); h0 = sha(p); size = os.path.getsize(p)
ss = save.SaveSessions(); d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
signal.signal(signal.SIGXFSZ, signal.SIG_IGN); resource.setrlimit(resource.RLIMIT_FSIZE, (size // 2, resource.RLIM_INFINITY))
try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); raise SystemExit('FAIL: save reported success under a write limit')
except SystemExit: raise
except Exception as e: err = type(e).__name__
resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
assert sha(p) == h0, 'original changed by a failed save'
left = [f for f in os.listdir(base) if f.endswith(('.tmp', '.part', '.sgtmp'))]; assert not left, left
for b in save.backups(p): assert sha(b['path']) == h0, 'a backup with wrong content is listed: %s' % b
print('in-place write-limit failure OK: %s, original intact, no temp, backups (%d) valid' % (err, len(save.backups(p))))
