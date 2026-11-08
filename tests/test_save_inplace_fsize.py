"""In-place SAVE with a write failure (RLIMIT_FSIZE = half the output, stand-in for a full disk): refused with an error, source byte-identical, no temp leftovers; after lifting the limit the same save works."""
import os, sys, asyncio, tempfile, shutil, json, hashlib, signal, resource
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ro'}); assert r.status == 200, await r.text()
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN); lo = resource.getrlimit(resource.RLIMIT_FSIZE)
        resource.setrlimit(resource.RLIMIT_FSIZE, (os.path.getsize(src) // 2, lo[1]))
        try: r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json()
        finally: resource.setrlimit(resource.RLIMIT_FSIZE, lo)
        print('inplace under fsize limit', r.status, json.dumps(j)[:140])
        assert r.status >= 400 and sha(src) == h0 and not [f for f in os.listdir(_T) if 'sgtmp' in f or f.endswith('.part')], (r.status, j)
        r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json(); assert r.status == 200 and sha(src) != h0, (r.status, j)
    print("in-place fsize-limit OK: 507-style refusal, source unchanged; after lifting the limit the save works")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
