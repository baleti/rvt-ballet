"""A RESTORE that is refused (corrupt backup) must leave the file AND the pending edit list as they were. Local sample only (skips without it)."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = 'cache'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ.setdefault('RVTBALLET_EDITSTORE', _T + '/es'); os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    import aiohttp
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1365188, 'dx': 2.0}); assert r.status == 200
        r = await c.post('/api/m/m/save', json={}); assert r.status == 200, await r.text()
        h1 = sha(src)
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1365188, 'dx': 1.0}); assert r.status == 200, await r.text()
        files = [os.path.join(rt, n) for rt, _, ns in os.walk(_T + '/c') for n in ns if '.rvt.' in n and not n.endswith('.part')]; assert files, 'no backup'
        for f in files: b = bytearray(open(f, 'rb').read()); b[len(b) // 2] ^= 1; open(f, 'wb').write(bytes(b))      # every backup corrupt
        r = await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); assert r.status >= 400, r.status
        assert sha(src) == h1, 'refused restore changed the file'
        ops = (await (await c.get('/api/m/m/edits')).json())['ops']; assert len(ops) == 1, ('pending edit lost by a refused restore', ops)
    print('restore refusal keeps edits OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
