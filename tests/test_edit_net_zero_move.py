"""Net-zero MOVE (+1 then -1 on column 301595, 2024 cols2): the output is byte-identical to the source or the save is refused fail-closed with not_applied; a single +1 move saves and differs."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        EID = 301595
        M = lambda dx: c.post('/api/m/m/edit', json={'op': 'move', 'eid': EID, 'dx': dx})
        async def sa(name):
            out = os.path.join(_T, name); r = await c.post('/api/m/m/saveas', json={'dest': out, 'confirm': True}); t = (await r.text())[:300].replace('\n', ' '); return r.status, out, t
        r = await M(1.0); assert r.status == 200, await r.text()
        r = await M(-1.0); print('move +1 then -1', r.status, flush=True); assert r.status == 200, await r.text()
        st, out, t = await sa('net0.rvt'); print('net-zero move saveas', st, t[:200], flush=True)
        if st == 200: print('identical to source:', sha(out) == h0, flush=True); assert sha(out) == h0, 'net-zero move changed the file'
        else: assert st == 422 and 'not_applied' in t, (st, t)
        assert sha(src) == h0
        r = await c.post('/api/m/m/edit/undo', json={}); r = await c.post('/api/m/m/edit/undo', json={})
        r = await M(1.0); assert r.status == 200; st, out, t = await sa('plus1.rvt'); print('single +1', st, flush=True); assert st == 200, t; assert sha(out) != h0
    print('net-zero move: identical copy or fail-closed not_applied; a single move saves')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
