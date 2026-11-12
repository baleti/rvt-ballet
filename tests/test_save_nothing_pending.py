"""SAVE / SAVE AS with nothing pending (never edited, or edited then undone) and undo on an empty stack: a clean JSON answer, never a stack trace or 500, source untouched."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/files/e1_level_2024.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        EID, PAR = 12160, 'Angled Joins'
        P = save._read_params(open(src, 'rb').read())[EID]['params'].get(PAR)
        E = lambda v: c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': EID, 'param': PAR, 'value': v, 'kind': 'Int'})
        async def chk(label, r):
            t = await r.text()
            try: j = json.loads(t)
            except Exception: raise AssertionError('%s: not JSON (stack trace?): %r' % (label, t[:200]))
            print(label, r.status, j.get('code', 'ok'), str(j.get('error', ''))[:110], flush=True)
            assert r.status < 500 or r.status == 507, (label, r.status, t[:200]); assert os.path.exists(src) and sha(src) == h0, label
            return r.status, j
        # nothing pending at all
        await chk('save in place, no edits', await c.post('/api/m/m/save', json={'confirm': True}))
        await chk('saveas, no edits', await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'n1.rvt'), 'confirm': True}))
        # edit, undo, save
        r = await E(1 - P); assert r.status == 200, await r.text()
        r = await c.post('/api/m/m/edit/undo', json={}); print('undo', r.status, (await r.text())[:100], flush=True); assert r.status == 200
        await chk('save in place after undo', await c.post('/api/m/m/save', json={'confirm': True}))
        await chk('saveas after undo', await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'n2.rvt'), 'confirm': True}))
        # undo with nothing to undo
        r = await c.post('/api/m/m/edit/undo', json={}); print('undo on empty', r.status, (await r.text())[:100], flush=True); assert r.status < 500
        assert sha(src) == h0
    print('save with no edits, after undo-to-empty, and undo on empty: JSON answers (no 5xx except 507), source untouched')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
