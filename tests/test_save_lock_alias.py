"""Two processes save the SAME file in place through different path spellings (real path vs symlink alias vs ./x/../): the lock must be per file, not per spelling.
Process A is held at 'before_replace'; B (via symlink) must be refused (Locked), A then completes, source intact."""
import os, sys, tempfile, shutil, hashlib, subprocess, time
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
T = tempfile.mkdtemp()
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
A = r'''
import os, sys, time
sys.path.insert(0, %r)
from rvtballet import save
save._import()
import savegate as sg, savegate.atomic as AT
src = sys.argv[1]; flag = sys.argv[2]
def hook(s):
    if s == 'before_replace': open(flag, 'w').write('x'); time.sleep(40)
AT._hook = hook
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
save.save_overwrite(ss, 'm', src); print('A DONE')
''' % HERE
B = r'''
import os, sys
sys.path.insert(0, %r)
from rvtballet import save
save._import()
import savegate as sg
src = sys.argv[1]
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
try: save.save_overwrite(ss, 'm', src); print('B OK')
except Exception as e: print('B ERR', type(e).__name__, str(e)[:100])
''' % HERE
try:
    os.makedirs(T + '/real/sub'); src = T + '/real/src.rvt'; shutil.copy(RTE, src); h = sha(src)
    os.symlink(T + '/real', T + '/alias')
    env = dict(os.environ, SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c'); flag = T + '/flag'
    pa = subprocess.Popen([sys.executable, '-c', A, src, flag], env=env, stdout=subprocess.PIPE, text=True)
    for _ in range(300):
        if os.path.exists(flag): break
        time.sleep(1)
    else: raise SystemExit('A never reached before_replace')
    for spelling in (T + '/alias/src.rvt', T + '/real/sub/../src.rvt'):
        p = subprocess.run([sys.executable, '-c', B, spelling], env=env, capture_output=True, text=True, timeout=300)
        print(spelling.replace(T, ''), '->', p.stdout.strip() or p.stderr[-200:])
        assert 'B ERR Locked' in p.stdout, 'second save through an alias was not refused: ' + p.stdout
    out, _ = pa.communicate(timeout=120); print(out.strip())
    assert 'A DONE' in out and sha(src) == h
    print('OK')
finally:
    shutil.rmtree(T, ignore_errors=True)
