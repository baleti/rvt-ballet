"""SAVE (overwrite with a real edit) when the volume is full (rootless tmpfs via unshare): with 0 / 64 KB / 3 MB / 5.5 MB free the save must be refused (DiskError) with the original byte-identical, no leftovers;
with 8 MB free it succeeds and the new file passes the gate. Derived from test_restore_enospc.py. Skips when unshare or the scene is unavailable."""
import os, sys, subprocess, tempfile, shutil
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
SG = os.path.expanduser('~/src/savegate')
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
with open(os.path.join(d, 'filler'), 'wb') as f:
    try:
        while True: f.write(b'\0' * 65536); f.flush()
    except OSError: pass
fp = os.path.join(d, 'filler'); os.truncate(fp, max(0, os.path.getsize(fp) - int(os.environ['LEAVE_KB']) * 1024))
try: save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); print('SAVE ok')
except Exception as e: print('SAVE ERR', type(e).__name__, str(e)[:100])
h = sha(src)
sys.path.insert(0, %r)
from savegate.adapters import RvtAdapter
print('STATE', 'original' if h == h0 else 'new', 'damage', bool(RvtAdapter().source_damage(open(src, 'rb').read())))
print('LEFT', sorted(f for f in os.listdir(d) if f not in ('src.rvt', 'filler', '.savegate')))
'''
if not os.path.exists(RTE): print('skipped (scene missing)'); sys.exit(0)
bad = []; ran = 0
for leave, want in ((0, 'SAVE ERR'), (64, 'SAVE ERR'), (3000, 'SAVE ERR'), (5500, 'SAVE ERR'), (8000, 'SAVE ok')):
    T = tempfile.mkdtemp()
    try:
        m = T + '/mnt'; os.makedirs(m); open(T + '/c.py', 'w').write(CHILD % (HERE, T + '/j', T + '/c', RTE, SG))
        mb = os.path.getsize(RTE) // 1048576 * 2 + 6
        p = subprocess.run(['unshare', '-rm', 'sh', '-c', 'mount -t tmpfs -o size=%dm tmpfs %s && %s %s %s' % (mb, m, sys.executable, T + '/c.py', m)], capture_output=True, text=True, timeout=600, env=dict(os.environ, LEAVE_KB=str(leave)))
        out = p.stdout
        if 'STATE' not in out: print('skipped (unshare unavailable or setup failed)'); sys.exit(0)
        ran += 1
        ok = out.count(want) == 1 and 'damage False' in out and 'LEFT []' in out and (('STATE original' in out) == (want == 'SAVE ERR'))
        if not ok: bad.append((leave, out))
    finally: shutil.rmtree(T, ignore_errors=True)
assert not bad, bad
print('OK', ran, 'cases')
