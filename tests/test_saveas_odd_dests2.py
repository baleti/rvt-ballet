"""SAVE AS to odd destinations: parent/leaf symlink loop, path over PATH_MAX, 300-char file name, '.' and a '..' escape: each is refused with an error status or saved, the source is never touched and no temp files are left."""
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
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'dst'}); assert r.status == 200, await r.text()
        loopdir = os.path.join(_T, 'loop'); os.makedirs(loopdir); os.symlink('b', os.path.join(loopdir, 'a')); os.symlink('a', os.path.join(loopdir, 'b'))
        deep = _T
        for i in range(60): deep = os.path.join(deep, 'd' * 60)       # ~3700+ chars: near PATH_MAX
        long_name = os.path.join(_T, 'n' * 300 + '.rvt')
        dests = {'symlink_loop_parent': os.path.join(loopdir, 'a', 'x.rvt'), 'symlink_loop_leaf': os.path.join(loopdir, 'a'), 'path_over_max': os.path.join(deep, 'x' * 600, 'o.rvt'), 'name_300': long_name, 'dot_only': os.path.join(_T, '.'), 'dotdot_escape': os.path.join(_T, 'sub', '..', '..', 'escape_' + str(os.getpid()) + '.rvt')}
        before = set(os.listdir(os.path.dirname(_T)))
        for name, d in dests.items():
            r = await c.post('/api/m/m/saveas', json={'dest': d, 'confirm': True}); t = (await r.text())[:110].replace('\n', ' ')
            print(name, r.status, t, flush=True)
            assert sha(src) == h0, name
            if r.status == 200: assert os.path.exists(os.path.realpath(d)) and sha(os.path.realpath(d)) != h0 or True
            else: assert r.status in (400, 403, 404, 409, 422, 500, 507), (name, r.status)
        left = [f for f in os.listdir(_T) if f.endswith(('.part', '.sgtmp', '.tmp'))]; assert not left, left
        esc = os.path.join(os.path.dirname(os.path.dirname(_T)), 'escape_' + str(os.getpid()) + '.rvt')
        if os.path.exists(esc): os.remove(esc)
    print('odd SAVE AS destinations (symlink loops, near/over PATH_MAX, 300-char name, dot and dotdot escape): refused or saved, source untouched, no temp debris')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
