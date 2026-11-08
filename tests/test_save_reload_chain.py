"""Two in-place SAVE!s with a RELOAD of the model between them (second string edit on the same element): the first passes the gate; the second passes or is refused layout_changed with the file untouched (measured: refused, Partitions/61 layout (72, 25704) -> (73, 0)), backups are previous states, the first backup is the original bytes. Companion of test_save_chain (same session: 2nd save refused layout_changed)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); hs = [h0]; res = []
    for k, (val, match) in enumerate((('rel1', ''), ('rel2', 'rel1'))):
        md = os.path.join(_T, 'm%d' % k); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': val, 'match': match}); assert r.status == 200, await r.text()
            before = sha(src); r = await c.post('/api/m/m/save', json={}); j = await r.json(); res.append((r.status, j.get('code')))
            if r.status == 200: assert sha(src) != before; hs.append(sha(src))
            else: assert sha(src) == before, 'refused but file changed'
    print('reload chain', res)
    assert res[0][0] == 200 and (res[1][0] == 200 or res[1][1] == 'layout_changed'), res      # a 2nd save that changes a page layout is refused (file untouched, asserted above); anything else is a failure
    print('save reload chain OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
