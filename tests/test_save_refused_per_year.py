"""In-place SAVE! (overwrite gate wide open) on the smallest local corpus file of every Revit year 2017-2026: unsupported years give a non-200 with the 'writable years' message and the file stays byte-identical with no temp/lock leftovers; supported years with no edit stay byte-identical too. Skips years absent."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'*': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CORP = os.path.expanduser('~/rvtfix/corpus')
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    models = server.Models(); n = 0
    async with TestClient(TestServer(server.make_app(models))) as c:
        for y in range(2017, 2027):
            d = '%s/%d' % (CORP, y)
            fs = sorted((os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith('.rvt')), key=os.path.getsize) if os.path.isdir(d) else []
            if not fs: print(y, 'skip'); continue
            w = os.path.join(_T, 'w%d' % y); os.makedirs(w); src = w + '/src.rvt'; shutil.copy(fs[0], src); h0 = sha(src)
            md = w + '/m'; os.makedirs(md); models.m['m%d' % y] = {'dir': md, 'name': 'a', 'src': src}
            r = await c.post('/api/m/m%d/save' % y, json={}); t = await r.text(); n += 1
            assert sha(src) == h0, '%d: source changed' % y
            assert not [f for f in os.listdir(w) if f.endswith(('.tmp', '.part', 'lock'))], '%d leftovers' % y
            if r.status != 200: assert r.status in (409, 415, 422, 507) and 'writable years' in t, (y, r.status, t[:200])
            print(y, r.status)
    print('per-year in-place save OK, %d years, sources untouched' % n)
asyncio.run(run())
