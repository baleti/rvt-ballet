"""disk-full style failure (RLIMIT_FSIZE, no sudo needed): in-place SAVE! with writes capped below the output size must fail cleanly: source byte-identical, no leftover temp/part files, and a later save without the cap works.
Synthetic 2024 .rte (local copy); skipped when absent."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json, signal, resource
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    d = os.path.join(_T, 'w'); os.makedirs(d); src = os.path.join(d, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'rotate', 'eid': 301595, 'deg': 30.0}); assert r.status == 200, await r.text()
        for cap in (lambda n: n - 1, lambda n: n * 9 // 10, lambda n: n // 2, lambda n: 4096):
            soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
            resource.setrlimit(resource.RLIMIT_FSIZE, (cap(os.path.getsize(src)), hard))
            try: r = await c.post('/api/m/m/save', json={}); j = await r.json()
            finally: resource.setrlimit(resource.RLIMIT_FSIZE, (soft, hard))
            print('capped save ->', r.status, j.get('code') or j.get('error', '')[:80])
            assert r.status != 200, 'save claimed success under a write cap'
            assert sha(src) == h0, 'capped save changed the source'
            left = [f for f in os.listdir(d) if f != 'src.rvt']; assert not left, left
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('uncapped retry ->', r.status, j.get('code') or j.get('verify', {}).get('n_unexpected'))
        assert r.status == 200 and j['verify']['n_unexpected'] == 0 and sha(src) != h0
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
