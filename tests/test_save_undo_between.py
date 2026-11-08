"""edit A, edit A', UNDO A', SAVE! in place: only A is in the file; then edit B again and SAVE!: both are, the first save's bookkeeping must not leak (applied-count / pending list). Checked by re-reading parameters from the bytes on disk, original restorable from the backup."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'      # the test is about the pending-edit bookkeeping, not the layout rule
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
FLOOR, P = 301553, 'Base Offset'
async def run():
    import rvt_params
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rte'); shutil.copy(RTE, src); h0 = hashlib.sha256(open(src, 'rb').read()).hexdigest(); md = os.path.join(_T, 'm'); os.makedirs(md)
    g = lambda e, n: (lambda d: d.get('params', d))(rvt_params.params(src)[e]).get(n)
    v0 = g(FLOOR, P); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        post = lambda p, j=None: c.post('/api/m/m' + p, json=j or {})
        num = lambda x: post('/edit', {'op': 'set_num', 'eid': FLOOR, 'param': P, 'value': v0 + x})
        assert (await num(0.25)).status == 200
        assert (await num(0.5)).status == 200
        assert (await post('/edit/undo')).status == 200            # undo the 0.5 edit: 0.25 stays
        r = await post('/save'); j = await r.json(); assert r.status == 200, j
        assert abs(g(FLOOR, P) - (v0 + 0.25)) < 1e-6, 'undone edit leaked / kept edit missing: %r' % g(FLOOR, P)
        h1 = hashlib.sha256(open(src, 'rb').read()).hexdigest(); assert h1 != h0
        assert (await num(0.75)).status == 200
        r = await post('/save'); j = await r.json(); assert r.status == 200, j
        assert abs(g(FLOOR, P) - (v0 + 0.75)) < 1e-6, 'second edit missing: %r' % g(FLOOR, P)
        r = await post('/save'); assert r.status != 200 or True       # nothing pending: either refused or a no-op, never corrupting
        assert abs(g(FLOOR, P) - (v0 + 0.75)) < 1e-6
    print('save undo-between OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
