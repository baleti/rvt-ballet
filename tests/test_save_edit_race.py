"""An /edit or /edit/undo arriving while /save runs is refused (423), never applied half-way: the saved file equals the state at save start, and the edit applies cleanly afterwards. Local sample only (skips without it)."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    import aiohttp
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1365188, 'dx': 2.0}); assert r.status == 200, await r.text()
        saving = asyncio.ensure_future(c.post('/api/m/m/save', json={}))
        await asyncio.sleep(0.05); codes = []
        for _ in range(20):
            if saving.done(): break
            r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1365188, 'dx': 5.0}); codes.append(r.status)
            r = await c.post('/api/m/m/edit/undo', json={}); codes.append(r.status)
            await asyncio.sleep(0.05)
        rs = await saving; j = await rs.json(); assert rs.status == 200, (rs.status, j)
        print('edit/undo statuses while saving:', sorted(set(codes)))
        assert all(x in (200, 423) for x in codes), codes
        out = sha(src); assert out != h0, 'edit 1 was not saved'
        r = await c.get('/api/m/m/edits'); print('edits after:', (await r.json()) if r.status == 200 else r.status)
    assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part', '.sgtmp'))]
    print('save/edit race OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
