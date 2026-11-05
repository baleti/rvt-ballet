"""c2x-rvtmatrix item 20: wall time of SAVE AS (move of one FamilyInstance) in a FRESH process, with the persistent snapshot/params cache dir given by env CACHE (run twice: cold, then warm). Prints seconds per stage. usage: CACHE=dir tools/rvt_repeat_save_time.py FILE"""
import os, sys, asyncio, tempfile, shutil, time, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_SNAPSHOT_CACHE=os.environ['CACHE'])
import atexit; atexit.register(shutil.rmtree, _T, True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in ('~/rvt-research', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
import rvt_geometry as G
from rvtballet import server
async def main(src):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    t0 = time.time(); work = os.path.join(_T, 'w.rvt'); shutil.copy(src, work); ix = G.file_geometry_index(work); ids = [e for e, v in ix.items() if str(v) == 'FamilyInstance'][:60]; t_ix = time.time() - t0
    models = server.Models(); md = tempfile.mkdtemp(dir=_T); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        t = time.time(); assert (await (await c.get('/api/m/m/saveinfo')).json()).get('open'); t_open = time.time() - t
        for e in ids:
            r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': e, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})
            if r.status == 200: break
        t = time.time(); r = await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'o.rvt')}); j = await r.json(); t_save = time.time() - t
    print(json.dumps({'status': r.status, 'index_s': round(t_ix, 1), 'open_s': round(t_open, 1), 'saveas_s': round(t_save, 1), 'total_s': round(time.time() - t0, 1)}))
asyncio.run(main(sys.argv[1]))
