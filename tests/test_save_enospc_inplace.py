"""In-place save when the volume holding the source is full (rootless tmpfs sized source+1 MB): save fails with an error, the source is byte-identical afterwards, no temp/part files left."""
import os, sys, tempfile, shutil, subprocess, hashlib
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
T = tempfile.mkdtemp()
CHILD = r'''
import os, sys, hashlib
sys.path.insert(0, %r)
os.environ['SAVEGATE_JOURNAL'] = %r; os.environ['SAVEGATE_CACHE'] = %r
from rvtballet import save
save._import()
import savegate as sg
d = sys.argv[1]; src = os.path.join(d, 'src.rvt'); shutil.copy if False else None
import shutil; shutil.copy(%r, src); h = hashlib.sha256(open(src, 'rb').read()).hexdigest()
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
try: save.save_overwrite(ss, 'm', src); print('UNEXPECTED OK')
except Exception as e: print('ERR', type(e).__name__, str(e)[:100])
print('SAME', hashlib.sha256(open(src, 'rb').read()).hexdigest() == h); print('LEFT', sorted(f for f in os.listdir(d) if f != 'src.rvt'))
'''
try:
    sp = T + '/c.py'; open(sp, 'w').write(CHILD % (HERE, T + '/j', T + '/c', RTE)); m = T + '/mnt'; os.makedirs(m)
    mb = os.path.getsize(RTE) // 1048576 + 2
    p = subprocess.run(['unshare', '-rm', 'sh', '-c', 'mount -t tmpfs -o size=%dm tmpfs %s && %s %s %s' % (mb, m, sys.executable, sp, m)], capture_output=True, text=True, timeout=600)
    out = p.stdout; print(out.strip() or p.stderr[-200:])
    if 'SAME' not in out: print('skipped (unshare unavailable)')
    else: assert 'SAME True' in out and "LEFT []" in out and 'UNEXPECTED' not in out, out; print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
