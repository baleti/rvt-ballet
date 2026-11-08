"""Pending edits and undo through the API, then in-place SAVE!: edit A, undo, edit B -> only B is in the saved file (A is not); edit then undo everything -> in-place save leaves the file byte-identical; after a save the op list is empty (no replay on the next save)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, hashlib, json, sqlite3
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
json.dump({'rvt': {'2024': 'open'}}, open(T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = T + '/m.rte'; shutil.copy(S, src); h0 = sha(src); md = T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    mv = lambda e: {'op': 'move', 'eid': e, 'dx': 1.0}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        assert (await c.post('/api/m/m/edit', json=mv(301595))).status == 200
        r = await c.post('/api/m/m/edit/undo', json={}); assert r.status == 200, r.status
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 200 and sha(src) == h0, ('empty-ops in-place save changed the file', r.status, j.get('error'))
        assert (await c.post('/api/m/m/edit', json=mv(301595))).status == 200; await c.post('/api/m/m/edit/undo', json={})
        assert (await c.post('/api/m/m/edit', json=mv(301596))).status == 200
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 200, j
        assert (await (await c.get('/api/m/m/saveinfo')).json())['pending_edits'] == 0, 'ops not cleared after save'
        h1 = sha(src); assert h1 != h0
        from rvtballet import edit
        only_b, _ = edit.apply_full(open(shutil.copy(S, T + '/ref.rte'), 'rb').read(), [edit.validate_op(mv(301596))]); assert hashlib.sha256(only_b).hexdigest() == h1, 'saved file is not exactly the surviving edit alone'
        r = await c.post('/api/m/m/save', json={}); assert r.status == 200 and sha(src) == h1, 'a second save replayed the ops'
    print('undo + in-place save OK: only the surviving edit saved, ops cleared, empty save is identity')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
