"""No-edit in-place SAVE! over corpus files (Autodesk samples) for every year: report status, byte identity, leftovers. usage: rvtsave_noedit_sweep.py FILE..."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, re
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'*': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def one(c, models, f, k):
    d = os.path.join(_T, 'w%d' % k); os.makedirs(d); src = os.path.join(d, 'src' + os.path.splitext(f)[1]); shutil.copy(f, src); h0 = sha(src)
    md = os.path.join(d, 'm'); os.makedirs(md); models.m['m%d' % k] = {'dir': md, 'name': 'a', 'src': src}
    r = await c.post('/api/m/m%d/save' % k, json={}); j = await r.json()
    same = sha(src) == h0; left = [x for x in os.listdir(d) if x.endswith(('.tmp', '.part', 'lock'))]
    print(os.path.basename(f)[:14], r.status, j.get('code', 'ok'), 'identical=%s' % same, 'leftovers=%s' % left, flush=True)
    shutil.rmtree(d, ignore_errors=True); return r.status in (200, 409, 415, 422, 507) and same and not left
async def run(fs):
    from aiohttp.test_utils import TestClient, TestServer
    models = server.Models(); bad = 0
    async with TestClient(TestServer(server.make_app(models))) as c:
        for k, f in enumerate(fs): bad += not await one(c, models, f, k)
    print('SWEEP files=%d bad=%d' % (len(fs), bad))
asyncio.run(run(sys.argv[1:]))
