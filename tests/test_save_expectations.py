"""SAVE AS result carries 'expectations' (QUEUE 88): what an independent Revit-API checker should find: from the COMPOSED ops (move +2 / -2 cancels and is not promised; last Comments wins; rotate kept)."""
import os, sys, asyncio, tempfile, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
T = 301595; C = 281147
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rte'); shutil.copy(RTE, src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    ops = [{'op': 'move', 'eid': T, 'dx': 2.0}, {'op': 'rotate', 'eid': T, 'deg': 30}, {'op': 'move', 'eid': T, 'dx': -2.0}, {'op': 'set_string', 'eid': C, 'param': 'Comments', 'value': 'first'}, {'op': 'set_string', 'eid': C, 'param': 'Comments', 'value': 'second'}]
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for o in ops: r = await c.post('/api/m/m/edit', json=o); assert r.status == 200, await r.text()
        dest = os.path.join(_T, 'out.rte'); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json(); assert r.status == 200, j
        json.dump(j['expectations'], open(os.path.join(_T, 'exp.json'), 'w'))
    exp = sorted(j['expectations'], key=lambda e: (e['eid'], e['kind']))
    want = sorted([{'eid': C, 'kind': 'param', 'name': 'Comments', 'value': 'second', 'type': 'String'}, {'eid': T, 'kind': 'rotate', 'deg': 30.0}], key=lambda e: (e['eid'], e['kind']))
    assert exp == want, exp
    assert save.expectations([{'op': 'delete', 'eid': 5}], [5, 7]) == [{'eid': 5, 'kind': 'absent'}, {'eid': 7, 'kind': 'absent'}]
    if os.environ.get('KEEP_EXPECT'): shutil.copy(dest, os.environ['KEEP_EXPECT'] + '/out.rte'); shutil.copy(os.path.join(_T, 'exp.json'), os.environ['KEEP_EXPECT'] + '/exp.json'); shutil.copy(src, os.environ['KEEP_EXPECT'] + '/orig.rte')
    print('save expectations OK:', exp)
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
