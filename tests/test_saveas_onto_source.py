"""(SAVE AS onto the source) dest spelled as the source itself, as a symlink to it, as a hard link to it, via ./ and ../dir segments, with overwrite+confirm: every spelling is refused ('destination is the source file') and the source is byte-identical afterwards."""
import os, sys, shutil, hashlib, tempfile, asyncio
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
from rvtballet import server
from aiohttp.test_utils import TestClient, TestServer
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    os.makedirs(T + '/d'); p = T + '/d/m.rte'; shutil.copy(S, p); h0 = sha(p)
    os.symlink(p, T + '/d/sym.rte'); os.link(p, T + '/d/hard.rte')
    spell = [p, T + '/d/./m.rte', T + '/d/../d/m.rte', T + '/d/sym.rte', T + '/d/hard.rte']
    md = tempfile.mkdtemp(dir=T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': p}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for d in spell:
            for ow in (False, True):
                r = await c.post('/api/m/m/saveas', json={'dest': d, 'overwrite': ow, 'confirm': True}); t = await r.text()
                print(os.path.relpath(d, T), ow, r.status, t[:90].replace('\n', ' '), flush=True)
                assert r.status in (400, 409, 422), (d, r.status, t[:200])
                assert sha(p) == h0, 'source changed by SAVE AS onto itself: ' + d
    print('OK: all spellings refused, source untouched')
asyncio.run(run()); sys.exit(0)
