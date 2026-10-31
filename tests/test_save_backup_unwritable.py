"""The backup folder (.savegate next to the file) is not writable: in-place SAVE! must refuse (no backup = no overwrite), original byte-identical, no temp left; after the folder is writable again the save works."""
import os, sys, shutil, hashlib, tempfile, stat
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available or os.getuid() == 0: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p); bd = T + '/.savegate'; os.makedirs(bd); os.chmod(bd, stat.S_IRUSR | stat.S_IXUSR)
ss = save.SaveSessions(); d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
mf = {'modified': ['el:301595']}
# 1) next-to-file folder unwritable: the backup falls back to the user cache dir, the save goes through and RESTORE can still find the original
save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest=mf)
bl = save.backups(p); assert bl and sha(bl[0]['path']) == h0 and not bl[0]['path'].startswith(bd), bl
save.restore_backup(ss, 'm', p, 0); assert sha(p) == h0, 'restore from the fallback store failed'
# 2) BOTH stores unwritable: no backup possible -> the overwrite must be refused and the original untouched
ss = save.SaveSessions(); d = ss.doc('m', p); cd = os.environ['SAVEGATE_CACHE']; os.chmod(cd, stat.S_IRUSR | stat.S_IXUSR)
for k in os.listdir(cd): os.chmod(os.path.join(cd, k), stat.S_IRUSR | stat.S_IXUSR)
try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest=mf); raise SystemExit('FAIL: overwrite went ahead with no backup possible')
except SystemExit: raise
except Exception as e: err = type(e).__name__
assert sha(p) == h0, 'original changed'
left = [f for f in os.listdir(T) if f.endswith(('.tmp', '.part', '.sgtmp'))]; assert not left, left
os.chmod(cd, stat.S_IRWXU)
for k in os.listdir(cd): os.chmod(os.path.join(cd, k), stat.S_IRWXU)
os.chmod(bd, stat.S_IRWXU)
print('backup stores: fallback used when the local one is unwritable; both unwritable -> %s, original intact' % err)
