"""Backup folder (.savegate symlink) on a different filesystem than the model (model on /dev/shm tmpfs): in-place SAVE! + RESTORE must work and be byte-exact, no temp left on either fs."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
if not os.path.isdir('/dev/shm') or os.stat('/dev/shm').st_dev == os.stat(T).st_dev: print('skip'); sys.exit(0)
M = tempfile.mkdtemp(dir='/dev/shm')
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = M + '/m.rte'; shutil.copy(S, p); h0 = sha(p)
os.makedirs(T + '/bk'); os.symlink(T + '/bk', M + '/.savegate')
ss = save.SaveSessions(); d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
assert sha(p) == hashlib.sha256(nb).hexdigest(), 'saved bytes differ from gate-approved bytes'
bl = save.backups(p); assert bl and sha(bl[0]['path']) == h0, bl
save.restore_backup(ss, 'm', p, 0); assert sha(p) == h0, 'restore not byte-identical'
left = [f for d_ in (M, T + '/bk') for f in os.listdir(d_) if f.endswith(('.tmp', '.part', '.sgtmp'))]; assert not left, left
shutil.rmtree(M); print('cross-filesystem backup: save ok, backup==original, restore byte-identical, no temp left')
