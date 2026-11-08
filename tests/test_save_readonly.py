"""overwrite of a source file that carries the read-only flag (chmod 444): refused up front with 409 code 'read_only' and the message that names the read-only state (it used to surface as a generic 500 'error'),
source bytes unchanged, no temp leftovers; after clearing the flag the same save works."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib
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
        os.chmod(src, 0o444)
        r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json()
        assert r.status == 409 and j['code'] == 'read_only' and 'read-only' in j['error'] and sha(src) == h0 and not [f for f in os.listdir(_T) if 'sgtmp' in f or f.endswith('.part')], (r.status, j)
        os.chmod(src, 0o644)
        r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json(); assert r.status == 200 and sha(src) != h0, (r.status, j)
    print('save readonly OK: 444 source -> 409 read_only (source unchanged); after chmod 644 the save works')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
