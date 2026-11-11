"""(c6x-rvtmatrix: SAVE AS onto a BACKUP) after an in-place SAVE! made a backup, SAVE AS with overwrite+confirm onto that backup file (or a new file inside the .savegate backup dir) must be refused and the backup bytes unchanged: a silent overwrite would destroy the only rollback."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
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
    md = tempfile.mkdtemp(dir=T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': p}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 301595, 'param': 'Comments', 'value': 'bk'}); print('edit', r.status, flush=True)
        r = await c.post('/api/m/m/save', json={}); t = await r.text(); print('save', r.status, t[:100], flush=True)
        r = await c.get('/api/m/m/backups'); bl = await r.json(); print('backups', len(bl), flush=True)
        bk = []
        for root, ds, fs in os.walk(T + '/d'):
            for f in fs:
                if os.path.join(root, f) != p: bk.append(os.path.join(root, f))
        assert bk, 'no backup file found (save refused?)'
        hb = {b: sha(b) for b in bk}; print('backup files', len(bk), flush=True)
        targets = bk + [os.path.join(os.path.dirname(bk[0]), 'new.rvt')]
        bad = 0
        for d in targets:
            for ow in (False, True):
                r = await c.post('/api/m/m/saveas', json={'dest': d, 'overwrite': ow, 'confirm': True}); t = await r.text()
                print(os.path.relpath(d, T), ow, r.status, t[:80].replace('\n', ' '), flush=True)
                if r.status == 200: bad += 1
        for b, h in hb.items(): assert os.path.exists(b) and sha(b) == h, 'BACKUP CHANGED ' + b
        print('FAIL accepted %d' % bad if bad else 'OK: backups intact'); sys.exit(1 if bad else 0)
asyncio.run(run())
