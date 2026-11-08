"""In-place save with source on one filesystem (home) and journal/cache/backups on another (tmpfs /tmp): identity save works, source identical, backup present and restorable, no temp left beside the source."""
import os, sys, tempfile, shutil, hashlib, subprocess
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
W = tempfile.mkdtemp(dir=os.path.expanduser('~'), prefix='.crossfs_'); C = tempfile.mkdtemp(dir='/dev/shm' if os.path.isdir('/dev/shm') else '/tmp')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CHILD = r'''
import os, sys
sys.path.insert(0, %r)
from rvtballet import save
save._import()
import savegate as sg
src = sys.argv[1]
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
try: save.save_overwrite(ss, 'm', src); print('RESULT OK')
except Exception as e: print('RESULT ERR', type(e).__name__, str(e)[:150])
'''
try:
    assert os.stat(W).st_dev != os.stat(C).st_dev, 'same filesystem, test meaningless'
    src = W + '/src.rvt'; shutil.copy(RTE, src); h = sha(src)
    env = dict(os.environ, SAVEGATE_JOURNAL=C + '/j', SAVEGATE_CACHE=C + '/c', SAVEGATE_BACKUPS='cache')
    p = subprocess.run([sys.executable, '-c', CHILD % HERE, src], capture_output=True, text=True, timeout=600, env=env)
    r = [l for l in p.stdout.splitlines() if l.startswith('RESULT')] or [p.stderr[-300:]]; print(r)
    assert r == ['RESULT OK'], r
    assert sha(src) == h
    assert os.listdir(W) == ['src.rvt'], os.listdir(W)
    bk = [os.path.join(d, f) for d, _, fs in os.walk(C) for f in fs if sha(os.path.join(d, f)) == h and 'src' in f]
    print('backups in cache fs:', len(bk)); assert bk, 'no backup copy found in the cache location'
    print('OK')
finally: shutil.rmtree(W, ignore_errors=True); shutil.rmtree(C, ignore_errors=True)
