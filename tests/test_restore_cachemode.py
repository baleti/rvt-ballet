"""SAVEGATE_BACKUPS=cache: SAVE then POST /restore through the API gives the original bytes back, nothing is created beside the model."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/data'; os.environ['SAVEGATE_BACKUPS'] = 'cache'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'*': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src)
    md = os.path.join(d, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 200, j
        assert not os.path.exists(os.path.join(d, '.savegate')), 'backup created beside the model in cache mode'
        r = await c.get('/api/m/m/backups'); bl = await r.json(); assert bl, bl
        os.truncate(src, os.path.getsize(src) // 2)         # damage the model
        r = await c.post('/api/m/m/restore', json={'confirm': True, 'n': len(bl) - 1 if isinstance(bl, list) else 0}); j = await r.json(); assert r.status == 200, (r.status, j)
    assert sha(src) == h0, 'restored bytes differ from the original'
    assert sorted(f for f in os.listdir(d) if f != 'm') == ['a.rvt'], os.listdir(d)
    print('restore (cache mode) OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
