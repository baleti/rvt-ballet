"""Items 139-141 on one element: a no-op set_string, two set_strings on the same param (last wins), and an edit followed by the original value (does the output equal the source?). Source untouched."""
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
        P = save._read_params(open(src, 'rb').read())[281147]['params'].get('Comments'); print('old Comments', repr(P), flush=True)
        async def sa(name):
            out = os.path.join(_T, name); r = await c.post('/api/m/m/saveas', json={'dest': out, 'confirm': True}); t = (await r.text())[:420].replace('\n', ' '); return r.status, out, t
        async def reset():
            r = await c.post('/api/m/m/edit/undo', json={'all': True}); return r.status
        E = lambda v: c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': v})
        # 139: no-op edit (same value as now)
        r = await E(P if isinstance(P, str) else ''); st, out, t = await sa('noop.rvt'); print('139 no-op edit', r.status, '| saveas', st, t[:420], flush=True)
        if st == 200: assert sha(out) == h0, 'a no-op edit must give a byte-identical copy'
        else: assert st == 422 and 'not_applied' in t, (st, t)      # net-zero edit: refused fail-closed (known UX gap, see c3x-progress item 139)
        # 141: two edits on the same element and param: last wins
        for i in range(5): await reset()
        await E('first'); await E('second'); st, out, t = await sa('last_wins.rvt'); print('141 two edits', st, t[:420], flush=True); assert st == 200, t
        got = save._read_params(open(out, 'rb').read())[281147]['params'].get('Comments'); assert got == 'second', got
        # 140: edit away then back to the original
        for i in range(5): await reset()
        await E('away'); await E(P if isinstance(P, str) else ''); st, out, t = await sa('back.rvt'); print('140 away and back', st, t[:420], flush=True)
        if st != 200: assert st == 422 and 'not_applied' in t, (st, t)
        if st == 200: print('140 identical to source:', sha(out) == h0, flush=True); got = save._read_params(open(out, 'rb').read())[281147]['params'].get('Comments'); assert got == P, (got, P)
        assert sha(src) == h0
    print('no-op / two edits / away-and-back on one element behave: results printed, source untouched')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
