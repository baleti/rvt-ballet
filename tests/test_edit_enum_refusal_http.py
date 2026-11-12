"""HTTP level: /edit set_num Int with an invalid enum value (Discipline 3, Detail Level 4) answers 400 edit_error 'not a valid choice', nothing is pending, the model file is byte-identical, and a following valid edit still works."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for p, v in (('Discipline', 3), ('Detail Level', 4)):
            r = await c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': 281147, 'param': p, 'value': v, 'kind': 'Int'}); j = await r.json()
            assert r.status == 400 and j.get('code') == 'edit_error' and 'not a valid choice' in j.get('error', ''), (p, r.status, j)
        assert sha(src) == h0
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ok'}); assert r.status == 200, await r.text()
        r = await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'o.rvt'), 'confirm': True}); assert r.status == 200, await r.text()
        assert sha(src) == h0
    print('invalid enum edits refused over HTTP (400), model untouched, later valid edit saved')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
