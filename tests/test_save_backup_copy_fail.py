"""In-place SAVE where the BACKUP copy fails (injected EIO in the backup stage): error, source byte-identical, no .part left in any store; retry works. Scenario B: first save OK, second save fails at its backup, the first save's result stays intact, third save works."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib, errno
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ro'}); assert r.status == 200, await r.text()
        import savegate.backup as bk
        def leftovers():
            out = []
            for root, ds, fs in os.walk(_T):
                out += [os.path.join(root, f) for f in fs if f.endswith(('.part', '.sgtmp'))]
            return out
        class Inj:
            def __init__(s): s.armed = False; s.hits = 0
        inj = Inj(); real = shutil.copyfileobj
        def bad(fsrc, fdst, *k):
            if inj.armed and getattr(fdst, 'name', '').endswith('.part'): inj.hits += 1; raise OSError(errno.EIO, 'injected I/O error in backup copy')
            return real(fsrc, fdst, *k)
        bk.shutil = type('S', (), {})(); [setattr(bk.shutil, n, getattr(shutil, n)) for n in dir(shutil) if not n.startswith('__')]; bk.shutil.copyfileobj = bad
        async def save():
            r = await c.post('/api/m/m/save', json={'confirm': True}); return r.status, await r.json()
        try:
            inj.armed = True; st, j = await save(); print('A: failing backup copy', st, json.dumps(j)[:140])
            assert st >= 400 and inj.hits >= 1 and sha(src) == h0 and not leftovers(), (st, inj.hits, leftovers())
            inj.armed = False; st, j = await save(); assert st == 200 and sha(src) != h0, (st, j); h1 = sha(src); print('A: retry saved')
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ro2'}); assert r.status == 200, await r.text()
            inj.armed = True; inj.hits = 0; st, j = await save(); print('B: second save with failing backup', st)
            assert st >= 400 and inj.hits >= 1 and sha(src) == h1 and not leftovers(), (st, inj.hits)
            inj.armed = False; st, j = await save(); assert st == 200 and sha(src) != h1, (st, j); print('B: third save saved')
            assert not leftovers()
        finally: bk.shutil = shutil
    print("failing backup copy OK: source unchanged each time, no .part/.sgtmp anywhere, retries work")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
