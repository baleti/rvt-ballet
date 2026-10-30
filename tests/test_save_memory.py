"""memory guard: with a tiny RVTPLAT_MEM_GB the save session refuses up front (saveinfo open=false + error, saveas -> 507 too_big), nothing read or written; with a normal budget it opens."""
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
        os.environ['RVTPLAT_MEM_GB'] = '0.02'
        i = await (await c.get('/api/m/m/saveinfo')).json(); assert i['open'] is False and 'needs roughly' in i['error'], i
        d = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': d}); j = await r.json()
        assert r.status == 507 and j['code'] == 'too_big' and not os.path.exists(d), (r.status, j)
        os.environ['RVTPLAT_MEM_GB'] = '16'
        i = await (await c.get('/api/m/m/saveinfo')).json(); assert i['open'] is True, i
        # element-count based estimate: the 5.6k-row scene is tiny in bytes, but at 5 GB per 1000 rows (absurd on purpose) it must be refused with the element count in the message
        c.app['saves'].close('m'); os.environ['RVTBALLET_SAVE_MEM_PER_ROW_KB'] = str(5 * 1024 * 1024)
        i = await (await c.get('/api/m/m/saveinfo')).json(); assert i['open'] is False and 'elements' in i['error'] and 'needs roughly' in i['error'], i
        os.environ.pop('RVTBALLET_SAVE_MEM_PER_ROW_KB')
    print('save memory OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
