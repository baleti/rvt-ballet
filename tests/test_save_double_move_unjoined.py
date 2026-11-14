"""# RVT_TEST_TIMEOUT=1800 (c5x-fam2020 item 90): +1 then -1 of the SAME unjoined column in one edit session must compose or be refused, never save a wrong value (replaces the joined-column premise of test_save_double_move, now refused by 483b07a). Synthetic scene."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')  # synthetic writer scene, unjoined column 301595 (membership {})
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
    mv = lambda dx: {'op': 'move', 'eid': 301595, 'dx': dx}
    h0 = sha(SRC); a = await one([mv(1.0), mv(-1.0)]); b = await one([mv(-1.0)])
    print('plus1_minus1:', a[:12], 'single_minus1:', b[:12], 'orig:', h0[:12])
    if b in ('refused_edit', 'refused_save'):   # 483b07a: 301595 is joined to 4 elements, Revit ignores its move (VM readback shift 0), so SAVE AS must refuse BOTH forms; a refusal is the safe outcome
        assert a in ('refused_edit', 'refused_save'), 'SEV1: double move saved while the single move is refused'; print('OK (joined element refused)'); return
    assert a in ('refused_edit', 'refused_save') or a != b, 'SEV2: +1 then -1 saved the same bytes as a single -1 move (edits do not compose)'
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
