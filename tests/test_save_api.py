"""POST /api/m/{mid}/saveas through aiohttp: source untouched, output byte-identical, refusals map to 4xx. Needs savegate + write-lab scene, else skips."""
import os, sys, asyncio, tempfile, hashlib, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
_T = __import__('tempfile').mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ.setdefault('SAVEGATE_CACHE', _T + '/c')
from rvtballet import server, save

async def run():
    from aiohttp.test_utils import TestClient, TestServer
    tmp = tempfile.mkdtemp(); src = os.path.join(tmp, 'a.rvt'); shutil.copy(RTE, src)
    h0 = hashlib.sha256(open(src, 'rb').read()).hexdigest()
    md = os.path.join(tmp, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m1'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        dest = os.path.join(tmp, 'out dir ä', 'b.rvt'); os.makedirs(os.path.dirname(dest))
        r = await c.post('/api/m/m1/saveas', json={'dest': dest}); j = await r.json()
        assert r.status == 200 and j['ok'], j
        assert hashlib.sha256(open(dest, 'rb').read()).hexdigest()[:12] == j['sha256'] == h0[:12] and j['version'] == '2024', j
        assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == h0
        r = await c.post('/api/m/m1/saveas', json={'dest': dest}); j = await r.json()
        assert r.status == 409 and j['code'] == 'exists', (r.status, j)
        r = await c.post('/api/m/m1/saveas', json={'dest': dest, 'overwrite': True, 'confirm': True}); j = await r.json()
        assert r.status == 200 and j['backup'], j
        assert (await c.post('/api/m/m1/saveas', data='x')).status == 400
        assert (await c.post('/api/m/nope/saveas', json={'dest': dest})).status == 404
        assert [f for f in os.listdir(os.path.dirname(dest)) if 'sgtmp' in f or f.endswith('.lock')] == []
    print('save api OK')

if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip: savegate or scene missing')
else: asyncio.run(run())
