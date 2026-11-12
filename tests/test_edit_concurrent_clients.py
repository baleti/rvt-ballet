"""8 clients POST /edit to ONE model at the same moment (3 distinct ops, repeated): every answer is 200/4xx, nothing is written to the source, and the SAVE AS result is byte-identical to the same 3 ops applied one after the other."""
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
        ops = [{'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'c1'}, {'op': 'move', 'eid': 301595, 'dx': 1.0}, {'op': 'move', 'eid': 301596, 'dx': 2.0}]
        # 8 clients fire the 3 ops (some twice) at the same moment
        rs = await asyncio.gather(*[c.post('/api/m/m/edit', json=ops[i % 3]) for i in range(8)])
        st = [r.status for r in rs]; print('concurrent edit statuses', st, flush=True)
        assert all(x in (200, 400, 409, 423) for x in st), st
        assert sha(src) == h0
        r = await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'conc.rvt'), 'confirm': True}); t = await r.text(); print('saveas', r.status, t[:120])
        assert r.status == 200, t
        # sequential reference with the same op set (dedupe of identical ops is allowed)
        models2 = server.Models(); md2 = os.path.join(_T, 'm2'); os.makedirs(md2); models2.m['m'] = {'dir': md2, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models2))) as c2:
        await c2.get('/api/m/m/saveinfo')
        for o in [ops[i % 3] for i, x in enumerate(st) if x == 200]:      # moves accumulate: the same multiset of accepted ops, one after the other
            r = await c2.post('/api/m/m/edit', json=o); assert r.status == 200, await r.text()
        r = await c2.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'seq.rvt'), 'confirm': True}); assert r.status == 200, await r.text()
    a_, b_ = sha(os.path.join(_T, 'conc.rvt')), sha(os.path.join(_T, 'seq.rvt')); print('concurrent', a_[:12], 'sequential', b_[:12])
    assert a_ == b_, 'concurrent edits produced a different file than the same ops applied one by one'
    assert sha(src) == h0
    print('8 concurrent edits (3 distinct ops, repeats) == the same ops applied sequentially, byte for byte; source untouched')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
