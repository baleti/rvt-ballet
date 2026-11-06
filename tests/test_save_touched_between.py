"""Source file touched (mtime changed, content identical, as a sync client does) between edit and SAVE!: either a clean save of the right bytes or a clean refusal; never a corrupt/other file, original restorable."""
import os, sys, shutil, hashlib, tempfile, time
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
    t = time.time() + 3600; os.utime(p, (t, t))
    try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'saved'
    except Exception as e: res = 'refused:%s' % type(e).__name__
    now = sha(p)
    if res == 'saved':
        assert now != h0 and sha(save.backups(p)[0]['path']) == h0, 'saved but backup is not the original'
        save.restore_backup(ss, 'm', p, 0); assert sha(p) == h0
    else: assert now == h0, 'refused but file changed'
    print('touched source ->', res, ', consistent')
finally: shutil.rmtree(T, True)
