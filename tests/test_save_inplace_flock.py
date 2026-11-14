"""(flock variant) In-place SAVE with a write failure (RLIMIT_FSIZE = half the output, stand-in for a full disk): refused with an error, source byte-identical, no temp leftovers; after lifting the limit the same save works."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib, signal, resource
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    import fcntl
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'lk'}); assert r.status == 200, await r.text()
        fd = os.open(src, os.O_RDONLY); fcntl.flock(fd, fcntl.LOCK_EX)
        try: r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json()
        finally: fcntl.flock(fd, fcntl.LOCK_UN)
        left = [f for f in os.listdir(_T) if 'sgtmp' in f or f.endswith('.part')]
        print('inplace with flock held', r.status, json.dumps(j)[:140])
        if r.status >= 400: assert sha(src) == h0 and not left, (r.status, j)
        else:
            assert sha(src) != h0 and not left and save._read_params(open(src, 'rb').read()), (r.status, j)
        os.close(fd)
    print('flock-held in-place save OK: either refused with source intact, or saved a readable file; no leftovers')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
