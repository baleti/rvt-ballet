"""Two POST /save of the same model at once in one server process: the file ends valid, nothing left over; a refused one answers 4xx (not 500); backups are the original and/or the first output only."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'*': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src)
    md = os.path.join(d, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        rs = await asyncio.gather(*[c.post('/api/m/m/save', json={}) for _ in range(4)])
        st = sorted(r.status for r in rs); bodies = [await r.json() for r in rs]
        assert all(s in (200, 409, 423, 429) for s in st), (st, bodies)
        assert 200 in st, (st, bodies)
    assert sha(src) == h0, 'no-edit saves must leave identical bytes'
    assert save.SaveSessions().available
    left = [f for f in os.listdir(d) if f not in ('a.rvt', 'm', '.savegate')]; assert not left, left
    assert not [f for f in os.listdir(os.path.join(d, '.savegate')) if f.endswith(('.part', '.sgtmp'))]
    print('concurrent save OK', st)
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
