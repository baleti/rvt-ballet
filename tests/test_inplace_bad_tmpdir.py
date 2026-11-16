"""In-place save AND restore with an unusable TMPDIR (nonexistent, read-only dir): the save completes (verified), the restore returns the original bytes exactly, nothing partial is left. Synthetic cols2 .rte (skips without it)."""
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
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); hs = sha(src)
assert hs != h0, 'edit did not change the file'
save.restore_backup(ss, 'm', src, 0); hr = sha(src)
print('RESULT', 'restored_original' if hr == h0 else 'saved' if hr == hs else 'OTHER')
print('LEFT', sorted(f for f in os.listdir(d) if f not in ('src.rte', '.savegate', 'j', 'c')))
'''
T = tempfile.mkdtemp(); fails = []
try:
    ro = os.path.join(T, 'ro'); os.makedirs(ro); os.chmod(ro, 0o555)
    for name, td in (('nonexistent', '/nonexistent/tmp'), ('readonly', ro)):
        d = os.path.join(T, name); os.makedirs(d)
        code = CHILD % (os.path.abspath(HERE), d + '/j', d + '/c', RTE)
        env = dict(os.environ, TMPDIR=td)
        r = subprocess.run([sys.executable, '-c', code, d], capture_output=True, text=True, env=env, timeout=1200)
        out = r.stdout + r.stderr; print(name, 'rc', r.returncode, out.strip()[-200:].replace('\n', ' | '))
        if r.returncode != 0 or 'RESULT restored_original' not in out or "LEFT []" not in out: fails.append(name)
finally: os.chmod(os.path.join(T, 'ro'), 0o755); shutil.rmtree(T, ignore_errors=True)
assert not fails, 'bad TMPDIR save/restore: %s' % fails
print('bad TMPDIR save and restore ok')
