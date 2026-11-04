"""RESTORE after another program replaced the saved file: the foreign version must be backed up before the restore overwrites it (no silent loss). Was: The file is modified behind the viewer's back with the SAME size and the SAME mtime (content changed only): in-place SAVE! must still notice (Conflict) and leave that other program's version untouched."""
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
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
foreign = b'FOREIGN-VERSION' * 1000; open(p, 'wb').write(foreign); hf = hashlib.sha256(foreign).hexdigest()
r = save.restore_backup(ss, 'm', p, 0)
assert sha(p) == h0, 'restore did not return the original'
bl = save.backups(p); print('backups after restore:', len(bl))
def content(path):
    raw = open(path, 'rb').read()
    return raw
found = [b for b in bl if foreign in content(b['path']) or hashlib.sha256(content(b['path'])).hexdigest() == hf]
print('foreign version held by %d backup(s)' % len(found))
assert found, 'foreign version was lost by the restore'
print('restore keeps the foreign version OK')
