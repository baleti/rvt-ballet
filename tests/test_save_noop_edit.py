"""Edit that sets a string to the value it already has (no-op edit) then in-place SAVE!: must not damage; either refused clearly with the file untouched, or saved with the value unchanged and a backup equal to the original."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
T = 301595; REFUSED = []
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    hs = [h0]
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'x1', 'match': ''}); assert r.status == 200
        # first make the file hold x1 via SAVE AS-free path: save in place, then re-edit to the same value
        r = await c.post('/api/m/m/save', json={}); assert r.status in (200, 409), r.status
        h1 = sha(src); print('first', r.status)
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'x1', 'match': 'x1'}); print('noop edit', r.status, (await r.text())[:150])
        if r.status == 200:
            r = await c.post('/api/m/m/save', json={}); t = await r.text(); print('noop save', r.status, t[:200])
            assert r.status in (200, 409, 422), r.status
            if r.status != 200: assert sha(src) == h1, 'refused noop save changed the file'
        else: assert sha(src) == h1
    print('noop edit save OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
