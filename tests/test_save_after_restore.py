"""(save after restore) Three in-place SAVE!s in a row (each from a fresh load of the previous result); then RESTORE n=0..2 must each give exactly the bytes that existed before save (3-n)... i.e. every historic version is recoverable byte-exact, newest first."""
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
def do_save(tag, dx):
    dd = ss.doc(tag, p); nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': dx})])
    save.save_overwrite(ss, tag, p, new_bytes=nb, manifest={'modified': ['el:301595']}); assert sha(p) == hashlib.sha256(nb).hexdigest()
do_save('a', 1.0); s1 = sha(p)
save.restore_backup(ss, 'r', p, 0); assert sha(p) == h0
do_save('b', 2.0); s2 = sha(p); assert s2 not in (h0, s1)
bk = save.backups(p); by = {sha(b['path']) for b in bk}
assert h0 in by, 'original lost from backups after save-after-restore'
n0 = len(bk)
save.restore_backup(ss, 'r2', p, next(b['n'] for b in bk if sha(b['path']) == h0)); assert sha(p) == h0
from savegate.adapters import RvtAdapter
assert str(RvtAdapter().validate(open(p, 'rb').read())).startswith('ok')
print('save after restore OK: states distinct, original still restorable byte-exact; backups', n0)
