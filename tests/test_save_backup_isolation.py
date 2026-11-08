"""Backups in the shared fallback store (user cache dir) are keyed by the file's directory: two different files with the SAME name in different folders never see or restore each other's backups."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile, stat
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'); S2 = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not (os.path.exists(S) and os.path.exists(S2)) or not save.SaveSessions().available or os.getuid() == 0: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
files = {}
for tag, src in (('A', S), ('B', S2)):
    d = T + '/' + tag; os.makedirs(d + '/.savegate'); os.chmod(d + '/.savegate', stat.S_IRUSR | stat.S_IXUSR)      # force the shared fallback store
    p = d + '/m.rte'; shutil.copy(src, p); files[tag] = (p, sha(p))
ssA = save.SaveSessions(); pA = files['A'][0]; dA = ssA.doc('m', pA)
nbA, _ = edit.apply_full(dA.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ssA, 'm', pA, new_bytes=nbA, manifest={'modified': ['el:301595']})
bA = save.backups(pA); bB = save.backups(files['B'][0])
assert bA and sha(bA[0]['path']) == files['A'][1], 'A has no backup of its own original'
assert not bB, 'B (never saved) is shown A\'s backup: %s' % bB
for tag in 'AB': os.chmod(T + '/' + tag + '/.savegate', stat.S_IRWXU)
print('fallback backups are isolated per directory: B sees none of A\'s')
