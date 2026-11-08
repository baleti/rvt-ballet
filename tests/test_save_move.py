"""move op (rvtedit backend): FamilyInstance 301595 moved by dx=2 ft: SAVE AS verify clean (manifest only that element), re-convert: its bounding box shifted by exactly (2,0,0) feet and no other element's
bounding box/row changed; invalid moves (zero, NaN, wledit backend) refused."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
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
        for bad in ({'dx': 0, 'dy': 0}, {'dx': float('nan')}, {'dx': 'x'}, {'dx': 1e9}, {'dx': 5e5}):
            r = await c.post('/api/m/m/edit', json=dict({'op': 'move', 'eid': T}, **bad), skip_auto_headers=()) if bad.get('dx') == bad.get('dx') else None
            if r is not None: assert r.status == 400, (bad, r.status)
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': T, 'dx': 2.0}); j = await r.json(); assert r.status == 200 and j['manifest'] == {'modified': ['el:%d' % T]}, (r.status, j)
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json(); assert r.status == 200 and j['verify']['n_unexpected'] == 0, (r.status, j.get('error'), j.get('report', {}).get('unexpected'))
    for name, f in (('src', src), ('out', out)):
        r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', f, os.path.join(_T, 'c_' + name)], capture_output=True, text=True, timeout=300); assert r.returncode == 0, r.stderr[-200:]
    a, b = bbs(_T + '/c_src'), bbs(_T + '/c_out'); moved = {i for i in a if i in b and a[i] != b[i]}
    assert moved == {T}, sorted(moved)[:5]
    d = [[b[T][k][x] - a[T][k][x] for x in range(3)] for k in (0, 1)]; assert all(abs(d[k][0] - 2.0) < 1e-6 and abs(d[k][1]) < 1e-6 and abs(d[k][2]) < 1e-6 for k in (0, 1)), d
    os.environ['RVTBALLET_EDIT_BACKEND'] = 'wledit'
    try: edit.validate_op({'op': 'move', 'eid': T, 'dx': 1.0}); raise SystemExit('FAIL: wledit accepted move')
    except edit.EditError as e: assert 'rvtedit backend' in str(e)
    print('save move OK: only element %d moved, bounding box shifted by %s ft' % (T, [round(v, 6) for v in d[0]]))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
