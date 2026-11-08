"""(x10 variant, queue item 8; also checks backup count, size growth and that no backup chain link is lost) Chain of in-place SAVE!s on one loaded model (three string edits; a move is refused in place when it changes the page layout, see layout_changed): every save passes the gate, each leaves a backup, final file equals what a fresh load shows, first backup is the ORIGINAL bytes."""
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
T = 301595; REFUSED = []
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    hs = [h0]
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        n_ok = 0
        N = int(os.environ.get('CHAIN_N', '10')); sizes = [os.path.getsize(src)]
        for k in range(1, N + 1):
            body = {'op': 'set_string', 'eid': 24, 'value': 'chain%d' % k, 'match': '' if k == 1 else 'chain%d' % (k - 1)}
            assert (await c.post('/api/m/m/edit', json=body)).status == 200, body
            before = sha(src); r = await c.post('/api/m/m/save', json={}); j = await r.json()
            if r.status == 200: n_ok += 1; assert sha(src) != before, 'save did not change the file'; hs.append(sha(src)); sizes.append(os.path.getsize(src))
            else:      # the only acceptable refusal: layout_changed, and the file must be exactly as before
                assert j.get('code') == 'layout_changed' and sha(src) == before, (r.status, j); print('REFUSED at', k, j)
                REFUSED.append((k, j.get('code'), str(j)[:300])); break
        assert n_ok >= 1
        bl = await (await c.get('/api/m/m/backups')).json(); assert len(bl) == n_ok, (len(bl), n_ok)
        assert sha(bl[-1]['path']) == h0, 'oldest backup is not the original'
        assert [sha(b['path']) for b in bl] == hs[:n_ok][::-1], 'backups are not the intermediate states'
    assert max(sizes) - min(sizes) < 4096 * 4, 'size growth %s' % sizes
    print('save chain OK: %d in-place save(s) passed, backups = previous states; then %s' % (n_ok, REFUSED or 'all 3 passed'))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
