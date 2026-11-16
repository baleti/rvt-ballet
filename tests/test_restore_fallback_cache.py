"""Backup folder beside the file is read-only (chmod 555 .savegate): the save falls back to the user cache location (SAVEGATE_CACHE) and completes; restore_backup then returns the ORIGINAL bytes from that fallback; nothing but src.rte/.savegate is left in the target dir. Synthetic cols2 .rte (skips without it)."""
import os, sys, tempfile, shutil, subprocess
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/c2x-cols2.rte')
if not os.path.exists(RTE): print('skip'); sys.exit(0)
CHILD = r'''
import os, sys, hashlib, shutil
sys.path.insert(0, %r)
os.environ['SAVEGATE_JOURNAL'] = %r; os.environ['SAVEGATE_CACHE'] = %r; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
d = sys.argv[1]; src = os.path.join(d, 'src.rte'); shutil.copy(%r, src); h0 = sha(src)
os.makedirs(os.path.join(d, '.savegate')); os.chmod(os.path.join(d, '.savegate'), 0o555)
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); hs = sha(src)
assert hs != h0, 'edit did not change the file'
cache_files = [os.path.join(dp, f) for dp, _, fs in os.walk(%r) for f in fs]
print('CACHEFILES', len(cache_files), 'BESIDE', len(os.listdir(os.path.join(d, '.savegate'))))
save.restore_backup(ss, 'm', src, 0); hr = sha(src)
print('RESULT', 'restored_original' if hr == h0 else 'saved' if hr == hs else 'OTHER')
print('LEFT', sorted(f for f in os.listdir(d) if f not in ('src.rte', '.savegate')))
'''
T = tempfile.mkdtemp(); d = os.path.join(T, 'w'); os.makedirs(d)
try:
    code = CHILD % (os.path.abspath(HERE), T + '/j', T + '/c', RTE, T + '/c')
    r = subprocess.run([sys.executable, '-c', code, d], capture_output=True, text=True, timeout=1200)
    out = r.stdout + r.stderr; print('rc', r.returncode, out.strip()[-300:].replace('\n', ' | '))
    ok = r.returncode == 0 and 'RESULT restored_original' in out and 'BESIDE 0' in out and 'LEFT []' in out and 'CACHEFILES 0' not in out
finally:
    try: os.chmod(os.path.join(d, '.savegate'), 0o755)
    except OSError: pass
    shutil.rmtree(T, ignore_errors=True)
assert ok, 'restore from the fallback backup failed'
print('restore from fallback cache ok')
