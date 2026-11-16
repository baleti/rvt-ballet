"""Source file replaced by another process (rename-over with different content) between edit and SAVE!: save must be refused or must not clobber the replacement; replacement bytes stay intact, no temp files left. Local sample only (skips without it)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ.setdefault('RVTBALLET_EDITSTORE', _T + '/es'); os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    import aiohttp
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1421396, 'dx': 2.0}); assert r.status == 200, await r.text()
        other = os.path.join(_T, 'other.rvt'); shutil.copy(SRC, other)
        with open(other, 'r+b') as f: f.seek(0, 2); f.write(b'REPLACED-BY-OTHER-PROCESS')
        h1 = sha(other); os.replace(other, src)
        rs = await c.post('/api/m/m/save', json={}); j = await rs.json()
        print('save after rename-over:', rs.status, str(j)[:200])
        assert sha(src) == h1 or rs.status != 200, 'replacement clobbered while reporting success'
        assert sha(src) == h1, 'replacement file was modified'
    assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part', '.sgtmp'))]
    print('replace-mid-edit OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
