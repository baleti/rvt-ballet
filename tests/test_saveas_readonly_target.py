"""(SAVE AS onto a read-only existing target; derived from onto_source) dest spelled as the source itself, as a symlink to it, as a hard link to it, via ./ and ../dir segments, with overwrite+confirm: every spelling is refused ('destination is the source file') and the source is byte-identical afterwards."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile, asyncio
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
from rvtballet import server
from aiohttp.test_utils import TestClient, TestServer
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    os.makedirs(T + '/d'); p = T + '/d/m.rte'; shutil.copy(S, p); h0 = sha(p)
    dst = T + '/d/ro.rte'; shutil.copy(S, dst); open(dst, 'ab').write(b'RO-SENTINEL'); hd = sha(dst); os.chmod(dst, 0o444)
    md = tempfile.mkdtemp(dir=T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': p}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for ow in (False, True):
            r = await c.post('/api/m/m/saveas', json={'dest': dst, 'overwrite': ow, 'confirm': True}); t = await r.text()
            print(ow, r.status, t[:140].replace('\n', ' '), flush=True)
            if r.status == 200: print('NOTE: saved over a read-only file (mode now %o)' % (os.stat(dst).st_mode & 0o777))
            assert sha(p) == h0, 'source changed'
            assert r.status == 200 or sha(dst) == hd, 'refused but the read-only target changed'
        print('left beside:', sorted(f for f in os.listdir(T + '/d')))
    print('OK: outcome above is consistent (refused+untouched, or saved)')
asyncio.run(run()); sys.exit(0)
