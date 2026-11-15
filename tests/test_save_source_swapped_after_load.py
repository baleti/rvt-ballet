"""SAVE! after the source file was replaced on disk by a different model (after load and after an edit was queued): must not overwrite it with the output built
from the old bytes. Replaced file stays byte-identical, no temp leftovers."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
D = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/')
A, B = D + '2024_writer_cols2.rte', D + '2024_writer_floors.rte'
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rte'); shutil.copy(A, src)
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'x', 'match': ''}); print('edit', r.status)
        shutil.copy(B, src); h1 = sha(src)
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('save', r.status, j.get('code'))
        assert r.status != 200, (r.status, j)
        assert sha(src) == h1, 'replaced source was overwritten'
        assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part')) or 'sgtmp' in f]
    print('OK swapped source not overwritten')
if not os.path.exists(A) or not os.path.exists(B) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
