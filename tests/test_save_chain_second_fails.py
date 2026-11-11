"""CHAIN: save 1 ok, then the 2nd in-place SAVE fails at the final os.replace (injected EIO): file stays byte-identical to the save-1 output, no leftovers, 3rd save works and contains both edits; restore n=0 returns to the save-1 state chain."""
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
        await c.get('/api/m/m/saveinfo')
        P = lambda e, v: {'op': 'set_string', 'eid': e, 'param': 'Comments', 'value': v}
        r = await c.post('/api/m/m/edit', json=P(281147, 'one')); assert r.status == 200, await r.text()
        r = await c.post('/api/m/m/save', json={'confirm': True}); assert r.status == 200, await r.text(); h1 = sha(src); assert h1 != h0
        r = await c.post('/api/m/m/edit', json=P(281147, 'two')); assert r.status == 200, await r.text()
        import savegate.atomic as at; real = os.replace
        def bad(a, b, *k):
            if os.path.realpath(b) == os.path.realpath(src): raise OSError(errno.EIO, 'injected I/O error at final replace')
            return real(a, b, *k)
        at.os = type('O', (), {})(); [setattr(at.os, n, getattr(os, n)) for n in dir(os) if not n.startswith('__')]; at.os.replace = bad
        try: r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json()
        finally: at.os = os
        print('2nd save with failing final replace', r.status, json.dumps(j)[:160])
        assert r.status >= 400 and sha(src) == h1 and not [f for f in os.listdir(_T) if 'sgtmp' in f or f.endswith('.part')], (r.status, j)
        r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json(); assert r.status == 200 and sha(src) != h1, (r.status, j)
        h3 = sha(src)
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); assert r.status == 200, await r.text(); assert sha(src) == h1, 'restore n=0 did not give the save-1 state'
    print("chain with failing 2nd save OK")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
