"""backups / restore / recover over HTTP: n backups listed, restore returns the byte-identical original, a SIGKILLed server leaves a journal that /api/recover lists."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, subprocess, signal, time
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'*': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src)
    md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        assert await (await c.get('/api/m/m/backups')).json() == []
        for k in range(3):                                   # three overwrites with (identity) content: 3 backups
            r = await c.post('/api/m/m/save', json={}); assert r.status == 200, await r.text()
        bl = await (await c.get('/api/m/m/backups')).json(); assert len(bl) == 3 and all(b['size'] == os.path.getsize(src) for b in bl), bl
        with open(src, 'ab') as f: f.write(b'garbage')       # damage the source outside the viewer
        assert (await c.post('/api/m/m/restore', json={})).status == 400          # confirm required
        j = await (await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0})).json(); assert j['ok'], j
        assert sha(src) == h0 and j['sha256'] == h0[:12], 'restore not byte-identical'
        assert len(await (await c.get('/api/m/m/backups')).json()) == 4          # the damaged file was backed up first
        j = await (await c.post('/api/m/m/restore', json={'confirm': True, 'n': 99})).json(); assert not j['ok'] and 'does not exist' in j['error'], j
        assert await (await c.get('/api/recover')).json() == []                   # our own live session is not 'crashed'
    # crash: a server process killed with SIGKILL leaves an unfinished journal
    code = "import sys; sys.path.insert(0, %r); from rvtballet import save; ss = save.SaveSessions(); ss.doc('x', %r); import time; print('up', flush=True); time.sleep(60)" % (os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), src)
    p = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE); assert p.stdout.readline().strip() == b'up'
    os.kill(p.pid, signal.SIGKILL); p.wait()
    app = server.make_app(models)
    async with TestClient(TestServer(app)) as c:
        rec = await (await c.get('/api/recover')).json()
        assert len(rec) == 1 and rec[0]['source'] == src and rec[0]['last'] == 'open', rec
    print('save restore/recover OK')

if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip: savegate or scene missing')
else: asyncio.run(run())
