"""SAVE AS destination hardening: relative, NUL, empty, trailing slash, missing folder, directory, symlink to the source (with and without overwrite), hardlink-free.
All must be 400 bad_dest (or 409 for existing) BEFORE any verify, and leave the source and its symlink untouched."""
import os, sys, asyncio, tempfile, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src)
    link = os.path.join(_T, 'link.rvt'); os.symlink(src, link)
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        cases = {'relative': 'out.rvt', 'nul': os.path.join(_T, 'a\0b.rvt'), 'blank': '   ', 'trailing-slash': _T + '/x/', 'dot': _T + '/.', 'missing-folder': _T + '/no/such/x.rvt',
                 'directory': _T, 'symlink-to-source': link, 'long': _T + '/' + 'a' * 5000}
        res = {}
        for name, dest in cases.items():
            for ow in (False, True):
                r = await c.post('/api/m/m/saveas', json={'dest': dest, 'overwrite': ow}); j = await r.json(); res[name + ('+ow' if ow else '')] = r.status
                assert r.status == 400 and j['code'] == 'bad_dest', (name, ow, r.status, j)
                assert sha(src) == h0 and os.path.islink(link) and os.readlink(link) == src
    print('save dest OK', res)
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
