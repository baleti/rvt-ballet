"""In-place SAVE of an edited model whose file is READ-ONLY (chmod 444) and whose directory is read-only: refused with a typed error, original bytes unchanged, no temp/partial file left."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, stat
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    d = os.path.join(_T, 'ro'); os.makedirs(d); src = os.path.join(d, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        assert (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'RO', 'match': ''})).status == 200
        os.chmod(src, 0o444); os.chmod(d, 0o555)
        try: r = await c.post('/api/m/m/save', json={}); t = await r.text()
        finally: os.chmod(d, 0o755); os.chmod(src, 0o644)
        if os.geteuid() == 0: print('skip (root ignores permissions)'); return
        assert r.status != 200, 'save into a read-only location was accepted: ' + t[:200]
    assert sha(src) == h0, 'read-only original changed'
    assert os.listdir(d) == ['src.rvt'], os.listdir(d)
    print('save read-only OK: refused (%d %s), original intact, directory clean' % (r.status, t[:160]))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
