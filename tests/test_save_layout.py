"""Second-generation edit (editing a file the writer already rewrote) re-pages the partition stream (full pages 72->73, last-page capacity 25704->0, +36864 B) and is NOT confirmed to open in Revit
(gen4/gen8 of the chain were unreachable in the VM). SAVE AS must carry a warning, overwrite must be refused (409 layout_changed) unless RVTBALLET_ALLOW_LAYOUT_CHANGE=1; a first-generation edit of the
Revit-written original keeps the layout: no warning. The gen-1 file is produced here by the viewer itself."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
EDIT = {'op': 'set_string', 'field': 'ParamValueAString.m_value', 'value': 'again-é', 'match': ''}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    async def session(src, mid):
        md = os.path.join(_T, 'm' + mid); os.makedirs(md); models = server.Models(); models.m[mid] = {'dir': md, 'name': 'a', 'src': src}; return models
    g0 = os.path.join(_T, 'gen0.rvt'); shutil.copy(RTE, g0); g1 = os.path.join(_T, 'gen1.rvt'); g2 = os.path.join(_T, 'gen2.rvt')
    async with TestClient(TestServer(server.make_app(await session(g0, 'a')))) as c:
        await c.get('/api/m/a/saveinfo'); await c.post('/api/m/a/edit', json=dict(EDIT, eid=24))
        j = await (await c.post('/api/m/a/saveas', json={'dest': g1})).json(); assert j['ok'] and 'warnings' not in j, j          # generation 1: layout kept, no warning
    async with TestClient(TestServer(server.make_app(await session(g1, 'b')))) as c:
        await c.get('/api/m/b/saveinfo'); await c.post('/api/m/b/edit', json=dict(EDIT, eid=25)); h1 = sha(g1)
        j = await (await c.post('/api/m/b/saveas', json={'dest': g2})).json(); assert j['ok'] and j['warnings'] and 'NOT confirmed' in j['warnings'][0], j     # generation 2: warned
        r = await c.post('/api/m/b/save', json={}); j = await r.json(); assert r.status == 409 and j['code'] == 'layout_changed' and sha(g1) == h1, (r.status, j)  # overwrite refused, file untouched
        os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'; r = await c.post('/api/m/b/save', json={}); assert r.status == 200, await r.text()               # explicit override works
    print('save layout OK (gen1 clean, gen2 warned + overwrite refused, override honoured)')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
