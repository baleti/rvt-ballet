"""Confirms the verification-worker memory cap on a REAL project: SAVE AS (no edit) with RVTBALLET_SNAPSHOT_MEM_GB=CAP through the API. Expected for a project that needs more than CAP: 507 too_big within minutes,
nothing written, the viewer still answering. Aggregate output only. usage: tools/save_real_cap.py FILE CAP_GB"""
import os, sys, asyncio, tempfile, time, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_MEM_GB'] = sys.argv[2]
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server
async def main(src):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}; t0 = time.time(); row = {'size_mb': round(os.path.getsize(src) / 2 ** 20, 1), 'cap_gb': float(sys.argv[2])}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); row['saveinfo_open'] = info.get('open'); row['saveinfo_error'] = (info.get('error') or '')[:100]
        dest = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json()
        row.update(status=r.status, code=j.get('code'), message=(j.get('error') or '')[:140], dest_written=os.path.exists(dest), viewer_alive=(await c.get('/api/m/m/saveinfo')).status == 200, seconds=round(time.time() - t0, 1))
    print(row); json.dump(row, open(_T + '/row.json', 'w'))
asyncio.run(main(sys.argv[1]))
