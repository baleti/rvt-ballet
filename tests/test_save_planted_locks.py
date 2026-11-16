"""Planted lock files next to the model: a LIVE lock (this pid), a fresh EMPTY lock (<10 s), garbage: SAVE and RESTORE refused (>=400), file and lock untouched; a lock of a DEAD pid (same host) is taken over and SAVE works, afterwards no lock is left"""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, threading, asyncio, tempfile, shutil, json, hashlib, errno
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
        import socket, subprocess, time
        from savegate import guard
        lp = guard._lock_path(src)
        # first an ordinary saved state so a backup exists for RESTORE
        st = (await c.post('/api/m/m/save', json={'confirm': True})).status; assert st == 200; h1 = sha(src)
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ro2'}); assert r.status == 200
        plants = {'live': json.dumps({'pid': os.getpid(), 'host': socket.gethostname(), 'time': time.time()}), 'empty': '', 'garbage': '\x00\xff not json'}
        for name, content in plants.items():
            open(lp, 'wb').write(content.encode('latin-1')); before = open(lp, 'rb').read()
            for ep, body in (('save', {'confirm': True}), ('restore', {'confirm': True, 'n': 0})):
                stop = threading.Event()
                def _fresh():      # a loaded host can spend >10 s before the lock is reached; keep the planted lock's mtime fresh (empty/garbage locks are only stale when old)
                    while not stop.wait(1.0):
                        try: os.utime(lp)
                        except OSError: pass
                th = threading.Thread(target=_fresh, daemon=True); th.start()
                try: r = await c.post('/api/m/m/' + ep, json=body); j = await r.json()
                finally: stop.set(); th.join()
                print(name, ep, r.status, j.get('code'), str(j.get('error'))[:200])
                assert r.status >= 400 and sha(src) == h1, (name, ep, r.status, j)
            assert open(lp, 'rb').read() == before, 'lock file of another holder was removed/changed: ' + name
            os.remove(lp)
        p = subprocess.Popen([sys.executable, '-c', 'pass']); p.wait()
        open(lp, 'w').write(json.dumps({'pid': p.pid, 'host': socket.gethostname(), 'time': time.time()}))
        r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json(); print('dead pid lock: save', r.status)
        assert r.status == 200 and sha(src) != h1, (r.status, j)
        assert not os.path.exists(lp), 'lock left behind after the save'
    print("live/empty/garbage locks refuse save and restore untouched; dead-pid lock is taken over; no lock left")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
