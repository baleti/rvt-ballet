"""Net-zero NUMERIC edits (Int toggle on e1_level 12160): a no-op set_num and an edit away and back are byte-identical copies or refused fail-closed with not_applied; a single flip saves and reads back."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/files/e1_level_2024.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        EID, PAR = 12160, 'Angled Joins'
        P = save._read_params(open(src, 'rb').read())[EID]['params'].get(PAR); print('old', PAR, repr(P), flush=True)
        async def sa(name):
            out = os.path.join(_T, name); r = await c.post('/api/m/m/saveas', json={'dest': out, 'confirm': True}); t = (await r.text())[:300].replace('\n', ' '); return r.status, out, t
        async def reset():
            r = await c.post('/api/m/m/edit/undo', json={'all': True}); return r.status
        E = lambda v: c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': EID, 'param': PAR, 'value': v, 'kind': 'Int'})
        r = await E(P); st, out, t = await sa('noop.rvt'); print('NUM no-op edit', r.status, '| saveas', st, t[:200], flush=True)
        if st == 200: assert sha(out) == h0
        else: assert st == 422 and 'not_applied' in t, (st, t)
        for i in range(5): await reset()
        await E(1 - P); await E(P); st, out, t = await sa('back.rvt'); print('NUM away and back', st, t[:200], flush=True)
        if st == 200: assert sha(out) == h0
        else: assert st == 422 and 'not_applied' in t, (st, t)
        for i in range(5): await reset()
        await E(1 - P); st, out, t = await sa('flip.rvt'); print('NUM single flip', st, flush=True); assert st == 200, t
        assert save._read_params(open(out, 'rb').read())[EID]['params'].get(PAR) == 1 - P
        assert sha(src) == h0
    print('numeric no-op and away-and-back: byte-identical or fail-closed not_applied; a single flip saves')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
