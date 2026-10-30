"""verification worker under a hard memory cap: with a tiny RVTBALLET_SNAPSHOT_MEM_GB the element dump worker dies / raises MemoryError and SAVE AS is refused cleanly (507 too_big, nothing written, viewer process alive and
still serving); with the normal limit the same save succeeds and is byte-identical; reader errors in the worker still map to 422 output_unreadable (test_save_unreadable)."""
import os, sys, asyncio, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        os.environ['RVTBALLET_SNAPSHOT_MEM_GB'] = '0.4'
        d1 = os.path.join(_T, 'o1.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': d1}); j = await r.json()
        assert r.status == 507 and j['code'] == 'too_big' and 'too large to verify' in j['error'] and not os.path.exists(d1) and sha(src) == h0, (r.status, j)
        assert (await c.get('/api/m/m/saveinfo')).status == 200            # the viewer is alive
        os.environ.pop('RVTBALLET_SNAPSHOT_MEM_GB')
        d2 = os.path.join(_T, 'o2.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': d2}); j = await r.json(); assert r.status == 200 and sha(d2) == h0, (r.status, j)
    print('save memcap OK: tiny cap -> 507 too_big (worker died, nothing written, viewer alive); normal cap -> identical save')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
