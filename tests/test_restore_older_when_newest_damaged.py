"""Two saves give backups n=0 (state after save 1) and n=1 (original). n=0 is damaged (flip, then truncate): restore n=0 is refused and the current file untouched; restore n=1 (intact) returns the original byte-exact"""
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
        async def save():
            r = await c.post('/api/m/m/save', json={'confirm': True}); return r.status, await r.json()
        st, j = await save(); assert st == 200, j; h1 = sha(src)
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ro2'}); assert r.status == 200
        st, j = await save(); assert st == 200, j; h2 = sha(src); assert len({h0, h1, h2}) == 3
        r = await c.get('/api/m/m/backups'); lst = await r.json(); assert len(lst) >= 2, lst
        b0 = lst[0]['path']; assert sha(b0) == h1, 'n=0 is not the state before save 2'
        for how in ('flip', 'truncate'):
            data = bytearray(open(b0, 'rb').read() if how == 'flip' else open(b0, 'rb').read())
            if how == 'flip': data[len(data) // 2] ^= 1
            else: data = data[:len(data) - 5000]
            open(b0, 'wb').write(bytes(data))
            r = await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); j = await r.json(); print(how, 'n=0 restore', r.status, json.dumps(j)[:140])
            assert r.status >= 400 and sha(src) == h2, (how, r.status)
        r = await c.post('/api/m/m/restore', json={'confirm': True, 'n': 1}); j = await r.json(); print('n=1 restore', r.status, json.dumps(j)[:120])
        assert r.status == 200 and sha(src) == h0, (r.status, j)
    print("damaged newest backup refused each way, intact older backup restores the original")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
