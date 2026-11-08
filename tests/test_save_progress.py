"""GET /api/m/{mid}/saveprogress: idle -> busy false; during an edited SAVE AS it reports changing stages (applying edits / reading ... / verifying and writing) with growing elapsed; idle again afterwards."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); assert (await (await c.get('/api/m/m/saveprogress')).json())['busy'] is False
        assert (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'p', 'match': ''})).status == 200
        t = asyncio.ensure_future(c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'o.rvt')})); seen = []; el = []
        while not t.done():
            p = await (await c.get('/api/m/m/saveprogress')).json()
            if p['busy'] and p['stage'] and (not seen or seen[-1] != p['stage']): seen.append(p['stage']); el.append(p['elapsed'])
            await asyncio.sleep(0.3)
        assert (await t).status == 200
        assert seen[0] == 'applying edits' and any(x.startswith('reading') for x in seen), seen
        assert el == sorted(el) and (await (await c.get('/api/m/m/saveprogress')).json())['busy'] is False
        print('save progress OK', seen)
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
