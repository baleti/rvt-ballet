"""The limited (light) verification must never write over the source: /save ignores light_verify, and SAVE AS with light_verify+confirm+overwrite to the SAME path (or a hard link / symlink of it) is refused; the source bytes never change."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/src.rte'; shutil.copy(S, src); h0 = sha(src); md = _T + '/m'; os.makedirs(md)
    os.link(src, _T + '/hard.rte'); os.symlink(src, _T + '/sym.rte')
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 301595, 'dx': 1.0}); assert r.status == 200
        for dest in (src, _T + '/hard.rte', _T + '/sym.rte', _T + '/./src.rte'):
            r = await c.post('/api/m/m/saveas', json={'dest': dest, 'overwrite': True, 'light_verify': True, 'confirm': True})
            assert r.status != 200 and sha(src) == h0, ('light SAVE AS over the source accepted', dest, r.status)
        r = await c.post('/api/m/m/save', json={'light_verify': True, 'confirm': True}); assert sha(src) == h0, 'in-place /save with light_verify changed the file'
    assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part', '.sgtmp'))]
    print('light verification never overwrites the source OK (same path, hard link, symlink, ./ path, /save)')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
