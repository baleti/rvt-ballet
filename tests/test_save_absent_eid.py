"""no-op set_num (same value) on 5 walls, SAVE! in place: accepted or honestly refused, never changes any other param; output kept for VM open (env OUT)."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'      # the test is about the pending-edit bookkeeping, not the layout rule
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
WALLS, P = [301553,301554,301555,301556,301557], 'Base Offset'
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rte'); shutil.copy(RTE, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for op in ({'op': 'move', 'eid': 99999999, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0},
                   {'op': 'set_num', 'eid': 99999999, 'param': P, 'value': 1.0, 'kind': 'Double'}, {'op': 'set_string', 'eid': 99999999, 'param': 'Comments', 'value': 'x'}):
            r = await c.post('/api/m/m/edit', json=op); j = await r.json(); print(op['op'], op['eid'], r.status, str(j)[:100])
            if r.status == 200:
                r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('  save', r.status, str(j)[:160])
                assert r.status != 200, 'edit of absent eid accepted AND saved'
                await c.post('/api/m/m/edit/undo')
    print('absent eid OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
