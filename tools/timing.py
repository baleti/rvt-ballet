"""cold / warm timing table. cold = empty reader cache AND empty viewer cache (private scratch dirs, nothing of the reader's real cache is touched or deleted);
reader-warm = reader cache filled, viewer caches empty; warm = converted model present.   usage: tools/timing.py FILE.rvt [...]"""
import sys, os, time, json, tempfile, shutil, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHILD = r'''
import sys, os, time, json
sys.path.insert(0, %r); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
os.environ['RVT_BALLET_CACHE'] = %r
import rvt_xcache; rvt_xcache.D = %r
from rvtballet import build
t = time.time(); m = build.convert(%r, %r, log=lambda *a: None); print(json.dumps({'total': round(time.time() - t, 1), **m['timings']}))
'''
def run(f, vcache, xcache, out):
    code = CHILD % (ROOT, vcache, xcache, f, out)
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else {'error': r.stderr[-300:]}
for f in sys.argv[1:]:
    tmp = tempfile.mkdtemp(prefix='rvtv-timing-'); xc = os.path.join(tmp, 'xcache'); vc = os.path.join(tmp, 'vcache'); os.makedirs(xc); os.makedirs(vc)
    print('==', os.path.basename(f), '%.0f MB' % (os.path.getsize(f) / 1e6), flush=True)
    c = run(f, vc, xc, os.path.join(tmp, 'o1')); print('cold (reader + viewer caches empty):', c, flush=True)
    shutil.rmtree(vc); os.makedirs(vc)
    w1 = run(f, vc, xc, os.path.join(tmp, 'o2')); print('reader warm, viewer caches empty:   ', w1, flush=True)
    w2 = run(f, vc, xc, os.path.join(tmp, 'o3')); print('all caches warm (re-convert):        ', w2, flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
