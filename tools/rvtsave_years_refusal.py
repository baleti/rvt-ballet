"""c3x-rvtsave: per Revit year, smallest Autodesk sample from ~/rvtfix/corpus/<year>: set_string Comments on the first element that accepts it, then in-place SAVE! (overwrite on, DEFAULT gate).
Prints one aggregate row per year: edit status, save status/code, source sha unchanged?  Invariant: any non-200 save leaves the file byte-identical. usage: rvtsave_years_refusal.py [years...]"""
import os, sys, asyncio, tempfile, hashlib, shutil, glob, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_ALLOW_OVERWRITE='1', RVT_BALLET_CACHE=_T + '/bc', RVT_CORE_CACHE=_T + '/cc')
import atexit; atexit.register(shutil.rmtree, _T, True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
from rvtballet import server
import rvt_params
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def one(y):
    fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/%s/*.rvt' % y)), key=os.path.getsize)
    if not fs: return y, 'no sample'
    work = os.path.join(_T, 'w%s.rvt' % y); shutil.copy(fs[0], work); h0 = sha(work)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm%s' % y); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        si = await (await c.get('/api/m/m/saveinfo')).json()
        try: eids = sorted(rvt_params.params(work))[:40]
        except Exception as e: eids = []
        es = 'none'
        for e in eids:
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': 'Comments', 'value': 'c3x'}); es = r.status
            if es == 200: break
        r = await c.post('/api/m/m/save', json={}); j = await r.json()
    return y, 'size_mb=%d saveinfo_open=%s edit=%s save=%s code=%s untouched=%s' % (os.path.getsize(work) >> 20, si.get('open'), es, r.status, j.get('code'), sha(work) == h0 or r.status == 200)
async def main():
    for y in (sys.argv[1:] or range(2017, 2027)):
        try: print(*await one(y), flush=True)
        except Exception as e: print(y, 'ERROR', repr(e)[:150], flush=True)
asyncio.run(main())
