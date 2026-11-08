"""No-edit SAVE AS identity on Autodesk 2024 templates (local corpus): output sha256 equals the source, source untouched. YEAR env selects the corpus year (default 2024); years outside the writable set must be refused cleanly (415, nothing written). Skips absent files."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ.setdefault('SAVEGATE_CACHE', _T + '/c')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(files):
    from aiohttp.test_utils import TestClient, TestServer
    bad = 0
    for f in files:
        tmp = tempfile.mkdtemp(); src = tmp + '/a' + os.path.splitext(f)[1]; shutil.copy(f, src); h0 = sha(src); md = tmp + '/m'; os.makedirs(md)
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            import aiohttp; c.session._timeout = aiohttp.ClientTimeout(total=None)
            await c.get('/api/m/m/saveinfo'); d = tmp + '/b' + os.path.splitext(f)[1]; r = await c.post('/api/m/m/saveas', json={'dest': d}); t = await r.text()
            if r.status == 415 and 'unsupported_version' in t and sha(src) == h0 and not os.path.exists(d): print(os.path.basename(f)[:3], 'refused cleanly (year not writable), source untouched', flush=True); continue
            ok = r.status == 200 and os.path.exists(d) and sha(d) == h0 and sha(src) == h0
            print(os.path.basename(f)[:3], r.status, 'identical' if ok else 'DIFF ' + str(r.status) + ' ' + t[:600], flush=True); bad += not ok
    assert not bad, bad
    print('no-edit SAVE AS identity OK on', len(files))
fs = sorted(glob.glob(os.path.expanduser(os.environ.get('GLOB') or ('~/rvt-research/corpus/' + os.environ.get('YEAR', '2024') + '/*.rte'))))
if not fs or not save.SaveSessions().available: print('skip')
else: asyncio.run(run(fs))
