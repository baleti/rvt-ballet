"""Refusals leave the file untouched: unsupported year (SAVE AS and in-place SAVE with the overwrite gate OPEN), unsupported edit op (copy), bad eid.
Autodesk sample from the local corpus (skip if absent); the real gate is never touched."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {y: 'open' for y in map(str, range(2015, 2028))}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2017/' + (sorted(os.listdir(os.path.expanduser('~/rvtfix/corpus/2017')))[0] if os.path.isdir(os.path.expanduser('~/rvtfix/corpus/2017')) else 'x'))
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'copy', 'eid': 1, 'dx': 1.0}); assert r.status in (400, 415), r.status
        r = await c.post('/api/m/m/save', json={}); assert r.status != 200, 'in-place save of an unsupported year was accepted'
        assert 'writable years' in (await r.text()), 'no clear message'
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); assert r.status != 200 and not os.path.exists(out)
    assert sha(src) == h0, 'source changed by a refused save'
    assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))], 'temp files left behind'
    print('save refusals OK (unsupported year in-place + SAVE AS, copy op): source untouched')
if not os.path.isfile(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
