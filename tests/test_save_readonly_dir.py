"""in-place save of a WRITABLE file inside a directory that is not writable (chmod 555; atomic temp+rename impossible): must be refused (not 200, not a 500 traceback), source bytes unchanged, no temp leftovers; after chmod 755 the save works. Related: test_save_readonly (file flag). Original doc: overwrite of a source file that carries the read-only flag (chmod 444): refused up front with 409 code 'read_only' and the message that names the read-only state (it used to surface as a generic 500 'error'),
source bytes unchanged, no temp leftovers; after clearing the flag the same save works."""
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    sd = os.path.join(_T, 'sd'); os.makedirs(sd); src = os.path.join(sd, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ro'}); assert r.status == 200, await r.text()
        if os.geteuid() == 0: print('skip (root)'); return
        os.chmod(sd, 0o555)
        try:
            r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json()
            assert r.status != 200 and r.status != 500 and sha(src) == h0 and os.listdir(sd) == ['a.rvt'], (r.status, j, os.listdir(sd))
            print('refused', r.status, j.get('code'), str(j.get('error'))[:120])
        finally: os.chmod(sd, 0o755)
        r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json(); assert r.status == 200 and sha(src) != h0, (r.status, j)
    print('save readonly dir OK: 555 directory -> refused, source unchanged, no leftovers; after chmod 755 the save works')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
