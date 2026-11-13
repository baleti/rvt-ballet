"""c3x-rvtlink: two moves of the SAME element in one edit session must compose or be refused, never silently save a wrong value (edit-lab SEV2: +1 then -1 ft saved -1). Product path, 2024 Snowdon Structural column 606069. Compares the +1,-1 result with a single -1 move."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')  # Autodesk sample, point-located column 606069
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer

async def one(ops):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp, subprocess
    d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'src.rvt'); shutil.copy(SRC, src); md = os.path.join(d, 'm'); os.makedirs(md)
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, d + '/c0'], capture_output=True, text=True); assert r.returncode == 0, r.stderr[-300:]
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for op in ops:
            r = await c.post('/api/m/m/edit', json=op)
            if r.status != 200: print('edit refused:', (await r.text())[:200]); return 'refused_edit'
        out = os.path.join(d, 'out.rvt')      # SAVE AS: the in-place SAVE is (correctly) refused for this joined column (group_or_option guard, c575f61)
        r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        if r.status != 200: print('save refused:', str(j)[:600]); return 'refused_save'
        assert j['verify']['n_unexpected'] == 0
    return sha(out)
async def run():
    mv = lambda dx: {'op': 'move', 'eid': 606069, 'dx': dx}
    h0 = sha(SRC); a = await one([mv(1.0), mv(-1.0)]); b = await one([mv(-1.0)])
    print('plus1_minus1:', a[:12], 'single_minus1:', b[:12], 'orig:', h0[:12])
    assert b not in ('refused_edit', 'refused_save'), 'single move must work or the test proves nothing'
    assert a in ('refused_edit', 'refused_save') or a != b, 'SEV2: +1 then -1 saved the same bytes as a single -1 move (edits do not compose)'
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
