"""Write failure mid-save (RLIMIT_FSIZE smaller than the output, the closest portable stand-in for a full disk): SAVE AS with overwrite+confirm onto an existing, valid destination must fail with an error and leave that destination byte-identical, no temp leftovers; a SAVE AS to a new destination must leave no partial file. Skips without savegate or scene."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, signal, resource
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ.setdefault('SAVEGATE_CACHE', _T + '/c')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    tmp = tempfile.mkdtemp(); src = tmp + '/a.rvt'; shutil.copy(RTE, src); h0 = sha(src)
    old = tmp + '/old.rvt'; shutil.copy(RTE, old); open(old, 'ab').write(b'')    # a valid existing destination
    ho = sha(old); md = tmp + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m1'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m1/saveinfo')
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN); lo = resource.getrlimit(resource.RLIMIT_FSIZE)
        resource.setrlimit(resource.RLIMIT_FSIZE, (os.path.getsize(src) // 2, lo[1]))
        try:
            r1 = await c.post('/api/m/m1/saveas', json={'dest': old, 'overwrite': True, 'confirm': True}); t1 = await r1.text()
            new = tmp + '/new.rvt'; r2 = await c.post('/api/m/m1/saveas', json={'dest': new}); t2 = await r2.text()
        finally: resource.setrlimit(resource.RLIMIT_FSIZE, lo)
        print('overwrite', r1.status, t1[:120].replace('\n', ' ')); print('new', r2.status, t2[:120].replace('\n', ' '))
        assert r1.status >= 400 and r2.status >= 400, 'write failure was reported as success'
        assert sha(old) == ho and sha(src) == h0, 'existing destination or source damaged'
        assert not os.path.exists(new), 'partial new file left'
        left = [f for f in os.listdir(tmp) if f not in ('a.rvt', 'old.rvt', 'm')]
        assert not left, left
    print('fsize-limit write failure OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
