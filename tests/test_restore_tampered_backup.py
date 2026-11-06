"""A backup with a flipped byte must not be restored silently over the current file: RESTORE refuses (or at least the result is never a corrupt model accepted without error); current file stays byte-identical on refusal."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.path.expanduser('~'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['SAVEGATE_BACKUPS'] = 'cache'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
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
    save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); hs = sha(p)
    bp = save.backups(p)[0]['path']; b = bytearray(open(bp, 'rb').read())
    for off in (len(b) // 2, 4096 + 100):
        b[off] ^= 0x40
    os.chmod(bp, 0o644); open(bp, 'wb').write(b)
    try: save.restore_backup(ss, 'm', p, 0); res = 'restored'
    except Exception as e: res = 'refused:%s' % type(e).__name__
    now = sha(p)
    if res == 'restored': raise SystemExit('FAIL: tampered backup was installed (sha %s, orig %s)' % (now[:8], h0[:8]))
    assert now == hs, 'current file changed on refused restore'
    print('tampered backup -> %s, current file untouched' % res)
finally: shutil.rmtree(T, True)
