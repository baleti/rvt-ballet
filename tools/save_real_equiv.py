"""On a REAL project: the same by-name Comments edit saved (a) with the element-level verify and (b) with LIMITED verification must give byte-identical output files (the limited tier only changes how the output is
checked, not what is written). Aggregate output only. usage: tools/save_real_equiv.py FILE"""
import os, sys, asyncio, tempfile, time, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src):
    pr = rvt_params.params(src); eid = next(e for e, d in pr.items() if g(d).get('Comments') == ''); del pr
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}; row = {'size_mb': round(os.path.getsize(src) / 2 ** 20, 1)}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo'); r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'equivalence test'}); assert r.status == 200
        t = time.time(); dl = os.path.join(_T, 'light.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dl, 'light_verify': True, 'confirm': True}); row['light_status'] = r.status; row['light_seconds'] = round(time.time() - t, 1)
        t = time.time(); dn = os.path.join(_T, 'full.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dn}); j = await r.json(); row['full_status'] = r.status; row['full_seconds'] = round(time.time() - t, 1); row['full_verify_diffs'] = (j.get('verify') or {}).get('n_unexpected')
    row['identical'] = os.path.exists(dl) and os.path.exists(dn) and sha(dl) == sha(dn); print(row)
asyncio.run(main(sys.argv[1]))
