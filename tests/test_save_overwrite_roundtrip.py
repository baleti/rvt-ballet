"""Edit -> SAVE (overwrite, temp gate file for this test only) -> source changed, reader shows the edit, backup holds the ORIGINAL bytes -> RESTORE -> source byte-identical to the original,
fingerprint consistent for a following save. The real gate (~/.config/savegate/gate.json) is never touched."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json, subprocess
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        i = await (await c.get('/api/m/m/saveinfo')).json(); assert i['allow_overwrite'] and i['gate_open'], i
        assert (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 24, 'value': 'Overwritten', 'match': ''})).status == 200
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 200 and j['backup'], (r.status, j)
        h1 = sha(src)
        assert sha(j['backup']) == h0, 'backup is not the original'
        assert (await (await c.get('/api/m/m/saveinfo')).json())['pending_edits'] == 0
        from rvtballet import edit as _e; sys.path.insert(0, _e.WL); import wlrec
        assert any(l[1] == 'ParamValueAString.m_value' and l[4] == 'Overwritten' for l in list(wlrec.Model(src).find(24))[0][3]), 'edit not in the overwritten file'
        bl = await (await c.get('/api/m/m/backups')).json(); assert len(bl) == 1 and sha(bl[0]['path']) == h0
        j = await (await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0})).json(); assert j['ok'], j
        assert sha(src) == h0, 'restore not byte-identical to the original'
        r = await c.post('/api/m/m/save', json={}); assert r.status == 200, await r.text()       # fingerprint was re-opened by restore: no false conflict
    print('save overwrite roundtrip OK (edited file differs: %s)' % (h1 != h0))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
