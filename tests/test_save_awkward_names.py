"""c2x-rvtwrite: in-place SAVE! when the source file name is awkward (spaces+unicode, 255 bytes, 250 bytes): temp / backup names derived from it must not exceed NAME_MAX; save succeeds with 0 unexpected diffs and a backup equal to the original, or refuses cleanly with the source untouched and no leftovers. Synthetic 2024 .rte; skipped when absent."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json, signal, resource
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    names = ['my model äöü 日本.rvt', 'a' * 251 + '.rvt', 'b' * 246 + '.rvt']
    for nm in names:
        d = os.path.join(_T, 'w' + str(len(nm))); os.makedirs(d); src = os.path.join(d, nm); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm' + str(len(nm))); os.makedirs(md)
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/edit', json={'op': 'rotate', 'eid': 301595, 'deg': 30.0}); assert r.status == 200, await r.text()
            r = await c.post('/api/m/m/save', json={}); j = await r.json()
            print(len(nm.encode()), 'bytes ->', r.status, j.get('code') or j.get('verify', {}).get('n_unexpected'))
            if r.status == 200: assert j['verify']['n_unexpected'] == 0 and sha(src) != h0 and j.get('backup') and sha(j['backup']) == h0
            else: assert sha(src) == h0, 'refused save changed the source'
            left = os.listdir(d); print('  files in dir:', len(left)); assert not [f for f in left if f.endswith(('.tmp', '.part'))], left
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
