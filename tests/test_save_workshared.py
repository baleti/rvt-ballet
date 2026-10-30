"""In-place SAVE of a model whose BasicFileInfo says Worksharing != 'Not enabled' (or is unreadable) is refused with code 'workshared', file untouched;
SAVE AS stays allowed; a normal (Not enabled) file still saves. Autodesk 2024 template; the worksharing state is forced via save.worksharing_state."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rte'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    assert save.worksharing_state(open(src, 'rb').read()) == 'Not enabled', 'parser'
    real = save.worksharing_state
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for forced in ('Central', 'Local', None):
            save.worksharing_state = lambda b, f=forced: f
            r = await c.post('/api/m/m/save', json={}); j = await r.json()
            assert r.status == 409 and j.get('code') == 'workshared', (forced, r.status, j)
            assert sha(src) == h0, 'refused save changed the file'
        out = os.path.join(_T, 'o.rte'); r = await c.post('/api/m/m/saveas', json={'dest': out}); assert r.status == 200 and sha(out) == h0, r.status
        save.worksharing_state = real
        r = await c.post('/api/m/m/save', json={}); assert r.status == 200, r.status
    assert sha(src) == h0 and not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]
    print('workshared in-place refusal OK (Central/Local/unreadable refused, SAVE AS and normal save fine)')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
