"""SAVE AS with an EMPTY edit list: either a byte-identical copy (seen on the 2024 HVAC sample) or a clean refusal, never a changed file; the source stays untouched."""
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
        out = os.path.join(_T, 'noedit.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out, 'confirm': True}); j = await r.text()
        print('saveas with no edits', r.status, j[:200])
        if r.status == 200: assert sha(out) == h0, 'a SAVE AS without edits must be a byte-identical copy'; assert sha(src) == h0
        else: assert not os.path.exists(out) and sha(src) == h0
    print("no-edit SAVE AS: identical copy or clean refusal")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
