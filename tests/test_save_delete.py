"""delete op (opt-in, rvtedit backend): refused unless RVTBALLET_ENABLE_DELETE=1; with it, the manifest lists the deleted ids and savegate verify REFUSES the delete of 301592 because its neighbour 301593 changes (documented current behaviour)."""
import os, sys, asyncio, tempfile, shutil, subprocess, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_DELETE_ANY'] = '1'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
TARGET = 301592
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
        # CURRENT BEHAVIOUR (documented, not a pass): rvtedit's delete of FamilyInstance 301592 leaves its neighbour 301593 with a broken category lookup
        # (Category|ElementId -2001330 -> -1, 'Bottom Cut Angle' gone), so savegate verify refuses the save (undeclared change of el:301593) and nothing is written.
        # (wledit.Editor.delete of the same element changed no other element in an earlier offline scout: the two paths disagree - question to rvtedit2.)
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        assert r.status == 422 and j['code'] == 'verify_failed' and not os.path.exists(out), (r.status, j.get('error'))
        assert j['report']['unexpected'] == [['changed', 'el:301593']] and j['edits'][0]['op'] == 'delete', j['report']
    print('save delete OK (documented refusal): delete of %d refused by verify, undeclared change on el 301593, nothing written' % TARGET)

if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
