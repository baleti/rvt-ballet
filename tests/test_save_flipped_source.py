"""one byte flipped at a random offset of the source (SEED env): record whether the gate refuses or accepts; never leaves a changed file after a refusal."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'      # the test is about the pending-edit bookkeeping, not the layout rule
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]

CUT = 4096
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rte'); shutil.copy(RTE, src)
    import random; random.seed(int(os.environ.get('SEED', '1'))); sz = os.path.getsize(src)
    with open(src, 'r+b') as f:
        off = random.randrange(sz // 4, sz - 4096); f.seek(off); b = f.read(1); f.seek(off); f.write(bytes([b[0] ^ 0xFF])); print('flip at', off, 'of', sz)
    orig = open(src, 'rb').read(); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 301595, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}); print('edit', r.status)
        r = await c.post('/api/m/m/save', json={}); t = await r.text(); print('save', r.status, t[:160])
    new = open(src, 'rb').read()
    if r.status == 200:
        print('ACCEPTED flipped source: output differs from source in', sum(1 for x, y in zip(orig, new) if x != y), 'bytes, size', len(orig), len(new))
    else:
        assert new == orig, 'refused but file changed'; print('refused, source byte-identical')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
