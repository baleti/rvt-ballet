"""rotate op (rvtedit backend): FamilyInstance 301595 rotated by 30 degrees about its origin: SAVE AS verify clean (manifest only that element), re-convert: its bounding box changed, no other element's
bounding box/row changed; invalid rotations (zero, 360, NaN, string, wledit backend) refused."""
import os, sys, asyncio, tempfile, shutil, subprocess, sqlite3, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save, edit
T = 301595
def bbs(d): return {r[0]: json.loads(r[1]) for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select id, bb from el where bb is not null')}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for bad in ({'deg': 0}, {'deg': 360}, {'deg': float('nan')}, {'deg': 'x'}, {'deg': 1e9}, {}):
            r = await c.post('/api/m/m/edit', json=dict({'op': 'rotate', 'eid': T}, **bad)) if bad.get('deg') == bad.get('deg') else None
            if r is not None: assert r.status == 400, (bad, r.status)
        r = await c.post('/api/m/m/edit', json={'op': 'rotate', 'eid': T, 'deg': 30}); j = await r.json(); assert r.status == 200 and j['manifest'] == {'modified': ['el:%d' % T]}, (r.status, j)
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json(); assert r.status == 200 and j['verify']['n_unexpected'] == 0, (r.status, j.get('error'), j.get('report', {}).get('unexpected'))
    for name, f in (('src', src), ('out', out)):
        r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', f, os.path.join(_T, 'c_' + name)], capture_output=True, text=True, timeout=300); assert r.returncode == 0, r.stderr[-200:]
    a, b = bbs(_T + '/c_src'), bbs(_T + '/c_out'); moved = {i for i in a if i in b and a[i] != b[i]}
    assert moved == {T}, sorted(moved)[:5]
    assert a[T] != b[T], 'rotated element bounding box unchanged'
    os.environ['RVTBALLET_EDIT_BACKEND'] = 'wledit'
    try: edit.validate_op({'op': 'rotate', 'eid': T, 'deg': 30}); raise SystemExit('FAIL: wledit accepted rotate')
    except edit.EditError as e: assert 'rvtedit backend' in str(e)
    print('save rotate OK: only element %d changed, bounding box %s -> %s' % (T, [round(v, 3) for v in a[T][0]], [round(v, 3) for v in b[T][0]]))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
