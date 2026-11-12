"""c2x-rvtwrite: in-place SAVE! when the source path is a symlink, has a second hardlink, or is read-only (0444). Invariant: either a clean save (0 unexpected diffs, backup equals original, no .tmp/.part left, every path that names the file is the original or the full new file) or a refusal with every name still byte-identical to the original."""
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
    for kind in ('symlink', 'hardlink', 'readonly'):
        d = os.path.join(_T, kind); os.makedirs(d); real = os.path.join(d, 'real.rvt'); shutil.copy(SRC, real); h0 = sha(real); md = os.path.join(_T, 'm' + kind); os.makedirs(md)
        if kind == 'symlink': src = os.path.join(d, 'via.rvt'); os.symlink(real, src); names = [real]
        elif kind == 'hardlink': src = os.path.join(d, 'other.rvt'); os.link(real, src); names = [real, src]
        else: src = real; os.chmod(real, 0o444); names = [real]
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/edit', json={'op': 'rotate', 'eid': 301595, 'deg': 30.0}); assert r.status == 200, await r.text()
            r = await c.post('/api/m/m/save', json={}); j = await r.json()
            print(kind, '->', r.status, j.get('code') or j.get('verify', {}).get('n_unexpected'))
            if r.status == 200:
                assert j['verify']['n_unexpected'] == 0 and j.get('backup') and sha(j['backup']) == h0
                new = sha(src); assert new != h0
                for n in names + [src]: assert sha(n) in (h0, new), kind + ': ' + n + ' is neither original nor the new file'
                print('  src is symlink:', os.path.islink(src), 'real changed:', sha(real) != h0, 'linked names:', [sha(n) == new for n in names])
            else:
                for n in names + [src]: assert sha(n) == h0, kind + ': refused save changed ' + n
            left = os.listdir(d); assert not [f for f in left if f.endswith(('.tmp', '.part'))], left
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
