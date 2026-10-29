"""regression (fuzz seed 4 chain 7): two edits whose combination the reader cannot decode used to give HTTP 500; now 422 output_unreadable, nothing written, source intact."""
import os, sys, asyncio, tempfile, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for e, v, m in ((15523, ' leading and trailing ', None), (138842, 'Ünïcödé 日本語 ✓', '')):
            assert (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'value': v, 'match': m})).status == 200
        d = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': d}); j = await r.json()
        assert r.status == 422 and j['code'] in ('output_unreadable', 'verify_failed') and not os.path.exists(d) and sha(src) == h0, (r.status, j)
    print('save unreadable OK ->', r.status, j['code'])
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
