"""c6x-rvtmatrix: POST /api/m/<id>/edit with a misspelt guard key answers a 4xx edit error (not 200, not 500) and records no edit. Synthetic 2024 cols2 scene."""
import os, sys, asyncio, tempfile, shutil, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_SNAPSHOT_CACHE=_T + '/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1')
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); sys.exit(0)
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/s.rvt'; shutil.copy(RTE, src); md = _T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        for body in ({'op': 'move', 'eid': 301595, 'dx': 1.0, 'dzz': 2}, {'op': 'delete', 'eid': 301595, 'force': True}):
            r = await c.post('/api/m/m/edit', json=body); j = await r.json(); print(body['op'], r.status, str(j.get('error'))[:70])
            assert 400 <= r.status < 500 and not j.get('ok'), (r.status, j)
        r = await c.get('/api/m/m/edits'); j = await r.json(); assert j['ops'] == [], j
    print('OK')
try: asyncio.run(run())
finally: shutil.rmtree(_T, ignore_errors=True)
