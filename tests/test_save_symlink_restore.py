"""SAVE! then RESTORE through a symlinked source: the link stays a link, the real file gets the save, backups(link) lists the backup made for the real file, restore puts the original back."""
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.makedirs(_T + '/real')
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'      # the synthetic scene's layout grows; not under test here
open(_T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
real = _T + '/real/r.rte'; shutil.copy(S, real); link = _T + '/link.rte'; os.symlink(real, link); h0 = sha(real)
ss = save.SaveSessions(); d = ss.doc('m', link)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', link, new_bytes=nb, manifest={'modified': ['el:301595']})
assert os.path.islink(link) and sha(real) == hashlib.sha256(nb).hexdigest() != h0, 'link replaced or real file not updated'
bl = save.backups(link); assert bl and sha(bl[0]['path']) == h0, bl
save.restore_backup(ss, 'm', link, 0)
assert os.path.islink(link) and sha(real) == h0, 'restore through the link did not bring the original back'
print('symlink save + restore OK')
