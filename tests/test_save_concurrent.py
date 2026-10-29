"""two simultaneous SAVE AS of one model: exactly one runs (200), the other gets 423 locked at once; an edit / undo POST during a save is refused with 423 (no race on the op list);
afterwards a third save works (busy flag released) and every output is byte-identical to the source."""
import os, sys, asyncio, tempfile, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src)
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); d = [os.path.join(_T, 'o%d.rvt' % i) for i in range(3)]
        t1 = asyncio.ensure_future(c.post('/api/m/m/saveas', json={'dest': d[0]})); await asyncio.sleep(1.0)
        r2 = await c.post('/api/m/m/saveas', json={'dest': d[1]}); j2 = await r2.json()
        assert r2.status == 423 and j2['code'] == 'locked' and not os.path.exists(d[1]), (r2.status, j2)
        re_ = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'x', 'match': ''}); assert re_.status == 423
        assert (await c.post('/api/m/m/edit/undo')).status == 423
        r1 = await t1; assert r1.status == 200
        assert sha(d[0]) == h0
        r3 = await c.post('/api/m/m/saveas', json={'dest': d[2]}); assert r3.status == 200 and sha(d[2]) == h0 and sha(src) == h0
        assert not [f for f in os.listdir(_T) if 'sgtmp' in f]
    print('save concurrent OK (423 for the second request, third succeeds)')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
