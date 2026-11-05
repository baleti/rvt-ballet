"""c2x-rvtmatrix item 13: move one LinearDimString by (1,0,0) ft on a private copy (rvtedit backend), SAVE AS, keep OUT.rvt and EXPECT.json (the 'expectations' of the SAVE AS result) for tools/rvt_expect_check.py (Revit VM readout of the dimension).
usage: tools/rvt_dim_move_expect.py FILE OUTDIR [ID]"""
import os, sys, asyncio, tempfile, shutil, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit')
import atexit; atexit.register(shutil.rmtree, _T, True)
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, H)
for p in ('~/rvt-research', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
import rvt_geometry as G
from rvtballet import server
async def main(src, od, eid):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    os.makedirs(od, exist_ok=True); work = os.path.join(_T, 'w.rvt'); shutil.copy(src, work)
    ix = G.file_geometry_index(work); ids = [e for e, v in ix.items() if str(v) == 'LinearDimString'] if eid is None else [eid]
    models = server.Models(); md = tempfile.mkdtemp(dir=_T); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        assert (await (await c.get('/api/m/m/saveinfo')).json()).get('open')
        for e in ids:
            r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': e, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}); j = await r.json()
            if r.status == 200: break
            print('refused', e, str(j.get('error'))[:100])
        else: print('NO_MOVABLE'); return
        dest = os.path.join(od, 'dim_move.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json(); print('saveas', r.status, str(j.get('error'))[:200])
        if r.status == 200: json.dump(j.get('expectations'), open(os.path.join(od, 'EXPECT.json'), 'w')); print('eid', e, 'expectations', json.dumps(j.get('expectations'))[:400])
asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None))
