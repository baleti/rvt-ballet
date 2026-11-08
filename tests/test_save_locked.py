"""SAVE (overwrite) while another live process holds the savegate lock: 423 locked, source untouched; once that process is dead the lock is stale and SAVE succeeds.
(Linux stand-in for 'file open / being saved elsewhere'; Windows sharing violations are retried by savegate and untested here.)"""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json, socket, subprocess, time
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'*': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    holder = subprocess.Popen(['sleep', '120']); lock = os.path.join(_T, '.src.rvt.savegate-lock')
    json.dump({'pid': holder.pid, 'host': socket.gethostname(), 'time': time.time()}, open(lock, 'w'))
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/save', json={}); j = await r.json()
        assert r.status == 423 and j['code'] == 'locked' and sha(src) == h0 and os.path.exists(lock), (r.status, j)
        holder.kill(); holder.wait()
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 200 and sha(src) == h0, (r.status, j)
        assert not os.path.exists(lock), 'lock left behind'
    print('save locked OK (423 while the holder lives, stale lock taken over after it died)')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
