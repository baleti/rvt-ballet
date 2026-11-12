"""In-place SAVE! after the model file was renamed away behind the viewer's back: refused (>=400), no new file appears at the old path, the moved file keeps its bytes, no temp debris; putting it back, the next save works or refuses safely."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'gone'}); assert r.status == 200, await r.text()
        moved = src + '.moved'; os.rename(src, moved)       # another program renames the model away after it was loaded
        r = await c.post('/api/m/m/save', json={'confirm': True}); t = (await r.text())[:160].replace('\n', ' '); print('in-place save with source renamed away', r.status, t, flush=True)
        assert r.status >= 400, 'SAVE! must refuse when the source file is gone'
        assert not os.path.exists(src), 'SAVE! must not create a new file at the old path'
        assert sha(moved) == h0
        left = [f for f in os.listdir(_T) if f.endswith(('.part', '.sgtmp', '.tmp'))]; assert not left, left
        os.rename(moved, src)
        r = await c.post('/api/m/m/save', json={'confirm': True}); t = (await r.text())[:160].replace('\n', ' '); print('after the file is back', r.status, t, flush=True)
        assert r.status in (200, 409, 423), r.status      # back in place: saves, or refuses via fingerprint, never corrupts
    print('source renamed away: in-place SAVE! refused, no file created at the old path, moved file untouched')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
