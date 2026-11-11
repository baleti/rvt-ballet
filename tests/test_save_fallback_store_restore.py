"""Primary (beside-the-file .savegate) backup store unusable (a plain FILE sits where the folder would go): the save uses the fallback cache store, /backups lists that backup, /restore n=0 returns the original byte-exact."""
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
        open(os.path.join(_T, '.savegate'), 'w').write('i am a file, not a folder')
        r = await c.get('/api/m/m/backups'); j0 = await r.json(); print('backups before', r.status, json.dumps(j0)[:120])
        r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json(); print('save', r.status, json.dumps(j)[:200])
        assert r.status == 200 and sha(src) != h0, (r.status, j)
        r = await c.get('/api/m/m/backups'); j1 = await r.json(); print('backups after', r.status, json.dumps(j1)[:300])
        lst = j1 if isinstance(j1, list) else j1.get('backups', [])
        assert len(lst) >= 1, 'save used the fallback store but /backups does not list it'
        assert open(os.path.join(_T, '.savegate'), 'rb').read() == b'i am a file, not a folder'
        r = await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); j = await r.json(); print('restore', r.status, json.dumps(j)[:160])
        assert r.status == 200 and sha(src) == h0, (r.status, j)
    print("fallback-store backup is listed and restorable")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
