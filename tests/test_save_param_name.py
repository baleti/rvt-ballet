"""string parameter edited by NAME (rvtedit backend): element 24 stores >= 8 string parameters that are all empty (Keynote, Model, Manufacturer, Comments, URL, Description x2, Mark...).
Editing 'Comments' changes exactly the Comments row (Keynote stays empty: the old edit-by-text would have hit the first empty one); an ambiguous name ('Description', two ids on the element)
is refused with 400; SAVE AS verify clean; wledit backend refuses name-addressed edits."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, subprocess, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save, edit
def table(d): return {(r[0], r[1]): r[2] for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select e.id, p.k, p.v from prm p join el e on e.i=p.i')}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'param': 'Description', 'value': 'x'}); j = await r.json(); assert r.status == 400 and 'candidate ids' in j['error'], (r.status, j)
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'param': 'Comments', 'value': 'edited by name'}); j = await r.json(); assert r.status == 200 and j['manifest'] == {'modified': ['el:24']}, (r.status, j)
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json(); assert r.status == 200 and j['verify']['n_unexpected'] == 0, (r.status, j.get('error'))
    for name, f in (('src', src), ('out', out)):
        r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', f, os.path.join(_T, 'c_' + name)], capture_output=True, text=True, timeout=300); assert r.returncode == 0, r.stderr[-200:]
    a, b = table(_T + '/c_src'), table(_T + '/c_out'); d = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
    assert d == {(24, 'Comments')} and b[(24, 'Comments')] == 'edited by name' and b.get((24, 'Keynote'), '') == '', sorted(d)[:5]
    os.environ['RVTBALLET_EDIT_BACKEND'] = 'wledit'
    try: edit.validate_op({'op': 'set_string', 'eid': 24, 'param': 'Comments', 'value': 'x'}); raise SystemExit('FAIL: wledit accepted a name-addressed edit')
    except edit.EditError as e: assert 'rvtedit backend' in str(e)
    print("save param-by-name OK: only (24, 'Comments') changed, Keynote untouched, ambiguous 'Description' refused")
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
