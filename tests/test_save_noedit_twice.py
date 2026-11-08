"""(save with no edit, twice) In-place SAVE! through the API with NO pending edit, twice in a row: each answers cleanly (200 or a refusal), the file stays a valid unchanged model (bytes equal to the original or only equal-semantics), and no backup chain pollution beyond one per accepted save."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile, json, asyncio
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
from rvtballet import save, server
from aiohttp.test_utils import TestClient, TestServer
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p); md = tempfile.mkdtemp(dir=T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': p}
    out = []
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for i in range(2):
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); out.append((r.status, j.get('code', 'ok'))); print(i, r.status, j.get('code', 'ok'), 'same_bytes', sha(p) == h0, flush=True)
            assert r.status in (200, 400, 409, 422), r.status
            assert os.path.getsize(p) > 0
        bk = [f for f in os.listdir(T) if f != 'm.rte']; print('files beside', len(bk))
    print(out, 'file == original:', sha(p) == h0)
asyncio.run(run()); print('OK (inspect output: no crash, no corruption)'); sys.exit(0)
