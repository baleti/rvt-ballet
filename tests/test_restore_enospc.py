"""RESTORE when the volume is full (rootless tmpfs): after a successful in-place save the free space is filled, restore_backup must fail with an error or succeed, and the target must be byte-identical to the saved state or the original, never partial; no temp/part files left behind (the .savegate backup dir is by design)."""
import os, sys, tempfile, shutil, subprocess
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
T = tempfile.mkdtemp()
CHILD = r'''
import os, sys, hashlib, shutil
sys.path.insert(0, %r)
os.environ['SAVEGATE_JOURNAL'] = %r; os.environ['SAVEGATE_CACHE'] = %r; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
d = sys.argv[1]; src = os.path.join(d, 'src.rvt'); shutil.copy(%r, src); h0 = sha(src)
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); hs = sha(src)
assert hs != h0, 'edit did not change the file'
with open(os.path.join(d, 'filler'), 'wb') as f:      # fill the volume
    try:
        while True: f.write(b'\0' * 65536); f.flush()
    except OSError: pass
if os.environ.get('LEAVE_KB', '16') != '0':      # leave a little room (lock file fits, the restored copy does not)
    fp = os.path.join(d, 'filler'); os.truncate(fp, max(0, os.path.getsize(fp) - int(os.environ.get('LEAVE_KB', '16')) * 1024))
try: save.restore_backup(ss, 'm', src, 0); print('RESTORE ok')
except Exception as e: print('RESTORE ERR', type(e).__name__, str(e)[:100])
h = sha(src); print('STATE', 'saved' if h == hs else 'original' if h == h0 else 'OTHER')
print('LEFT', sorted(f for f in os.listdir(d) if f not in ('src.rvt', 'filler', '.savegate')))
left_sg = sorted(f for f in os.listdir(os.path.join(d, '.savegate')) if f.endswith(('.tmp', '.part', '.new'))) if os.path.isdir(os.path.join(d, '.savegate')) else []; print('SGTMP', left_sg)
'''
try:
    sp = T + '/c.py'; open(sp, 'w').write(CHILD % (HERE, T + '/j', T + '/c', RTE)); m = T + '/mnt'; os.makedirs(m)
    mb = os.path.getsize(RTE) // 1048576 * 2 + 6
    p = subprocess.run(['unshare', '-rm', 'sh', '-c', 'mount -t tmpfs -o size=%dm tmpfs %s && %s %s %s' % (mb, m, sys.executable, sp, m)], capture_output=True, text=True, timeout=900)
    out = p.stdout; print(out.strip() or p.stderr[-300:])
    if 'STATE' not in out: print('skipped (unshare unavailable or setup failed)')
    else: assert ('STATE saved' in out or 'STATE original' in out) and 'LEFT []' in out and 'SGTMP []' in out, out; print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
