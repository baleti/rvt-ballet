"""verify_failed response names the elements that changed outside the declaration (class, id, name) and the pending edits, so the UI can show them (Level rename -> 31 dependents)."""
import os, sys, asyncio, tempfile, shutil, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
MODEL = os.environ.get('RVT_TEST_MODELDIR')           # converted dir of RTE (tools: ./rvt-ballet convert RTE DIR)
from rvtballet import server, save
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src)
    models = server.Models(); models.m['m'] = {'dir': MODEL, 'name': 'a', 'src': src, 'db': None}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        assert (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 355, 'value': 'Level 1 renamed', 'field': 'DatumPlane.m_text'})).status == 200
        r = await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'o.rvt')}); j = await r.json()
        assert r.status == 422 and j['code'] == 'verify_failed' and len(j['changed_detail']) == 12, j.get('changed_detail')
        assert all(x['cls'] for x in j['changed_detail']) and j['edits'][0]['eid'] == 355, j
        print('save changed_detail OK:', sorted({x['cls'] for x in j['changed_detail']}))
if not MODEL or not os.path.exists(RTE) or not save.SaveSessions().available: print('skip (set RVT_TEST_MODELDIR to a converted dir of the scene)')
else: asyncio.run(run())
