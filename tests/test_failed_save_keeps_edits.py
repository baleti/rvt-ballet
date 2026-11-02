"""A SAVE! that fails (verify, lock, disk error) leaves the file untouched AND the pending edits in place; a retry then succeeds. Local sample only (skips without it)."""
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
    sg = save._import(); real = sg.save
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1365188, 'dx': 2.0}); assert r.status == 200
        for exc in (sg.VerifyFailed('injected verify failure'), sg.Locked('injected lock'), sg.DiskError('injected disk error'), RuntimeError('injected crash')):
            def boom(*a, **k): raise exc
            sg.save = boom
            try: r = await c.post('/api/m/m/save', json={})
            finally: sg.save = real
            j = await r.json(); assert r.status >= 400 and r.status != 200, (type(exc).__name__, r.status, j)
            assert sha(src) == h0, 'failed save changed the file (%s)' % type(exc).__name__
            ops = (await (await c.get('/api/m/m/edits')).json())['ops']; assert len(ops) == 1, ('pending edit lost after', type(exc).__name__, ops)
            assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part', '.sgtmp'))]
        r = await c.post('/api/m/m/save', json={}); assert r.status == 200, (r.status, await r.text())      # retry works
        assert sha(src) != h0
    print('failed save keeps edits OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
