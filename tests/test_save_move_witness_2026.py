"""c5x-rvtread 15(e): a FamilyInstance move in a 2026 file (id width of the newer families) saves through the gate with the witness; the 2024-only test_save_move_witness does not cover it."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
json.dump({'rvt': {'2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/../2026_writer_house1.rte')
from rvtballet import server, save
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    for eid, want in ((303741, 'saved'),):
        src = os.path.join(_T, 'src%d.rte' % eid); shutil.copy(RTE, src); before = open(src, 'rb').read(); md = os.path.join(_T, 'm%d' % eid); os.makedirs(md)
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': eid, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})
            if r.status != 200: got = 'refused'; print(eid, 'edit refused', r.status)
            else:
                r = await c.post('/api/m/m/save', json={}); j = await r.json(); got = 'saved' if r.status == 200 else 'refused'; print(eid, r.status, str(j)[:200])
        assert got == want, (eid, got, want)
        if want == 'refused': assert open(src, 'rb').read() == before, 'original touched'
    print('move witness OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
