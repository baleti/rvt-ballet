"""One by-NAME numeric edit (set_num: Double 'Width Factor' of a TextNoteAttributes element, else the first stored named Double found) on a REAL project through the server API (rvtedit backend), SAVE AS with element-level verify,
read-back with the reader: the edited parameter must have the new value and no other parameter of that element may change. Aggregate output only. KEEP_DIR keeps the output locally for the Revit harness.
usage: tools/save_real_num.py FILE [CLASS]"""
import os, sys, asyncio, tempfile, time, json, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
os.environ.setdefault('RVT_GEOM', '1')
from rvtballet import server
import rvt_params, rvtedit
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, cls):
    t0 = time.time(); pr = rvt_params.params(src); base = {e: dict(g(d)) for e, d in pr.items()}; ed = rvtedit.Edit(src); pick = None
    for eid in list(pr)[:2000]:
        try: pn, i, r, log, q = ed.g.e.trace(eid)
        except Exception: continue
        if r['class'] != cls: continue
        for l in log:
            if l[1] == 'ParamValueDouble.m_paramId':
                v = int(str(l[4])[4:-1]); pid = v - (1 << 64) if v >= (1 << 63) else v; nm = rvt_params.PNAMES.get(str(pid)); val = base.get(eid, {}).get(nm) if nm else None
                if nm and isinstance(val, (int, float)): pick = (eid, nm, float(val)); break
        if pick: break
    del ed
    if not pick: print('NO_CANDIDATE'); return
    eid, nm, v0 = pick; nv = round(v0 + 0.25, 6); print('picked 1 element of', cls, 'param', nm, 'old', v0, 'new', nv, flush=True)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); print('open', info.get('open'), str(info.get('error', ''))[:100], flush=True)
        r = await c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': eid, 'param': nm, 'value': nv}); j = await r.json(); print('edit', r.status, str(j.get('error', ''))[:120], flush=True)
        if r.status != 200: return
        out = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        if r.status != 200: print('SAVE', r.status, j.get('code'), str(j.get('error'))[:200]); return
        a = base[eid]; b = g(rvt_params.params(out).get(eid)); ch = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
        ok = ch == {nm} and abs(b[nm] - nv) < 1e-9
        print('NUM-EDIT', {'verify_diffs': j['verify']['n_unexpected'], 'only_param_changed': ch == {nm}, 'value_ok': abs(b.get(nm, 1e9) - nv) < 1e-9, 'changed_n': len(ch), 'seconds': round(time.time() - t0), 'result': 'OK' if ok and j['verify']['n_unexpected'] == 0 else 'MISMATCH'})
        kd = os.environ.get('KEEP_DIR')
        if kd: os.makedirs(kd, exist_ok=True); shutil.copy(out, os.path.join(kd, 'num_edited.rvt'))
        os.remove(out)
asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'TextNoteAttributes'))
