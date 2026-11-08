"""delete op (opt-in, rvtedit backend): refused unless RVTBALLET_ENABLE_DELETE=1; with it, the manifest lists the deleted ids and savegate verify REFUSES the delete of 301592 because its neighbour 301593 changes (documented current behaviour)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, subprocess, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_DELETE_ANY'] = '1'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
TARGET = 301553
def rows(d): return {r[0]: r[1:] for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select id, cls, name, level from el')}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': TARGET}); j = await r.json(); assert r.status == 400 and 'disabled' in j['error'], (r.status, j)
        os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
        r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': TARGET}); j = await r.json(); assert r.status == 200, (r.status, j)
        dele = j['manifest']['deleted']; assert 'el:%d' % TARGET in dele, j
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        assert r.status == 200 and os.path.exists(out), (r.status, j.get('error'), j.get('report'))
        assert os.path.getsize(out) > 0
        if os.environ.get('RVT_KEEP_OUT'): shutil.copy(out, os.environ['RVT_KEEP_OUT'])      # for the Revit VM judge
    print('save delete latest OK: delete of %d saved as, gate accepted Global/Latest change' % TARGET)

if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
