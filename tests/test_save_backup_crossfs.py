"""Backup store on another filesystem (tmpfs /dev/shm) than the model: in-place SAVE! works, the backup is byte-identical to the original, RESTORE brings it back exactly."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.path.expanduser('~'))
SH = tempfile.mkdtemp(dir='/dev/shm') if os.path.isdir('/dev/shm') else None
if not SH or os.stat(SH).st_dev == os.stat(T).st_dev: print('skip'); sys.exit(0)
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = SH + '/c'; os.environ['SAVEGATE_BACKUPS'] = 'cache'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p)
    ss = save.SaveSessions(); d = ss.doc('m', p)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
    assert sha(p) != h0
    bl = save.backups(p); assert bl and sha(bl[0]['path']) == h0, bl
    save.restore_backup(ss, 'm', p, 0); assert sha(p) == h0, 'restore not byte-exact'
    left = [f for f in os.listdir(T) if f.endswith(('.tmp', '.part', '.sgtmp'))]; assert not left, left
    print('cross-fs backup store OK (backup on %s)' % os.path.dirname(bl[0]['path'])[:9]); assert bl[0]['path'].startswith(SH), bl[0]['path']; print('ok')
finally: shutil.rmtree(T, True); shutil.rmtree(SH, True)
