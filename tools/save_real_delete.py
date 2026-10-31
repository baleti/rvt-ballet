"""DELETE of one leaf element (cascade == itself) on a REAL project through the server API (rvtedit backend, RVTBALLET_ENABLE_DELETE=1 set here only): SAVE AS with element-level verify; the element must be gone from the
reader output and nothing else may differ. A refusal by verify is a valid (safe) outcome and is reported. Aggregate output only. KEEP_DIR keeps the output locally for the Revit harness.
usage: tools/save_real_delete.py FILE [CLASS]"""
import os, sys, asyncio, tempfile, time, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
os.environ.setdefault('RVT_GEOM', '1')
from rvtballet import server
import rvt_params, rvtedit
cls = sys.argv[2] if len(sys.argv) > 2 else 'FamilyInstance'
async def main(src):
    t0 = time.time(); pr = rvt_params.params(src); ed = rvtedit.Edit(src); pick = None
    for eid in list(pr)[:3000]:
        try: pn, i, r, log, q = ed.g.e.trace(eid)
        except Exception: continue
        if r['class'] != cls or ed.latest_partition(eid) != pn: continue
        try:
            if ed.cascade(eid) == [eid]: pick = eid; break
        except Exception: continue
    del ed
    if not pick: print('NO_CANDIDATE', cls); return
    print('picked 1 leaf element of', cls, flush=True)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); print('open', info.get('open'), flush=True)
        r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': pick}); j = await r.json(); print('edit', r.status, str(j.get('error', ''))[:150], 'manifest', j.get('manifest'), flush=True)
        if r.status != 200: return
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        if r.status != 200: print('SAVE', r.status, j.get('code'), str(j.get('error'))[:200]); return
        b = rvt_params.params(out); gone = pick not in b; rest = {e for e in pr if e != pick and (e not in b or pr[e] != b[e])}
        print('DELETE', {'verify_diffs': j['verify']['n_unexpected'], 'element_gone': gone, 'other_elements_changed': len(rest), 'seconds': round(time.time() - t0), 'result': 'OK' if gone and not rest and j['verify']['n_unexpected'] == 0 else 'MISMATCH'})
        kd = os.environ.get('KEEP_DIR')
        if kd: os.makedirs(kd, exist_ok=True); shutil.copy(out, os.path.join(kd, 'deleted.rvt'))
        os.remove(out)
asyncio.run(main(sys.argv[1]))
