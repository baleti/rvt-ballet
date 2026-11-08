"""(SAVE AS onto a directory / missing parent / empty dest: refused, no files created) (SAVE AS onto an existing OTHER file) without overwrite, and with overwrite but no confirm, must be refused and leave the other file byte-identical; (old doc: onto the source) dest spelled as the source itself, as a symlink to it, as a hard link to it, via ./ and ../dir segments, with overwrite+confirm: every spelling is refused ('destination is the source file') and the source is byte-identical afterwards."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
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
    other = T + '/d/other.rte'; open(other, 'wb').write(b'UNRELATED' * 1000); ho = sha(other)
    md = tempfile.mkdtemp(dir=T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': p}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        os.makedirs(T + '/d/sub')
        r = await c.post('/api/m/m/saveas', json={'dest': T + '/d/x.rfa'}); t = await r.text(); print('project->.rfa', r.status, t[:90], flush=True)
        assert r.status == 400 and not os.path.exists(T + '/d/x.rfa'), (r.status, t[:200])
        for body in ({'dest': T + '/d/sub'}, {'dest': T + '/d/sub', 'overwrite': True, 'confirm': True}, {'dest': T + '/nope/x/y.rte'}, {'dest': ''}):
            r = await c.post('/api/m/m/saveas', json=body); t = await r.text(); print(body, r.status, t[:90], flush=True)
            assert r.status >= 400 and sha(p) == h0 and os.path.isdir(T + '/d/sub') and not os.path.exists(T + '/nope'), (body, r.status, t[:200])
        for body in ({'dest': other}, {'dest': other, 'overwrite': False, 'confirm': True}, {'dest': other, 'overwrite': True}):
            r = await c.post('/api/m/m/saveas', json=body); t = await r.text()
            print(body, r.status, t[:90].replace('\n', ' '), flush=True)
            assert r.status in (400, 409, 422), (body, r.status, t[:200])
            assert sha(other) == ho and sha(p) == h0, 'file changed by refused SAVE AS'
    print('OK: existing other file protected, source untouched')
asyncio.run(run()); sys.exit(0)
