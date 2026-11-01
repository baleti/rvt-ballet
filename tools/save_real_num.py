"""One by-NAME numeric edit (set_num: Double 'Width Factor' of a TextNoteAttributes element, else the first stored named Double found) on a REAL project through the server API (rvtedit backend), SAVE AS with element-level verify,
read-back with the reader: the edited parameter must have the new value and no other parameter of that element may change. Aggregate output only. KEEP_DIR keeps the output locally for the Revit harness.
KIND=Int (env) edits a stored Int parameter instead (new value = NEWVAL env, else old % 3 + 1: valid for enum-like params such as Detail Level; yes/no params need NEWVAL=0|1).
POOL=1 (env): new value = another value of the same parameter that occurs elsewhere in the project (for enum-like Int parameters).
usage: tools/save_real_num.py FILE [CLASS]"""
import os, sys, asyncio, tempfile, time, json, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
os.environ.setdefault('RVT_GEOM', '1')
from rvtballet import server
import rvt_params, rvtedit
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, cls):
    KIND = os.environ.get('KIND', 'Double'); t0 = time.time(); pr = rvt_params.params(src); base = {e: dict(g(d)) for e, d in pr.items()}; ed = rvtedit.Edit(src); pick = None
    for eid in list(pr)[:2000]:
        try: pn, i, r, log, q = ed.g.e.trace(eid)
        except Exception: continue
        if r['class'] != cls: continue
        if os.environ.get('SINGLE_RECORD') and ed.latest_partition(eid) != pn: continue      # element with an older copy in an earlier partition: the reader read-back sees the OLD copy (QUEUE 58g)
        for l in log:
            if l[1] == 'ParamValue%s.m_paramId' % KIND:
                v = int(str(l[4])[4:-1]); pid = v - (1 << 64) if v >= (1 << 63) else v; nm = rvt_params.PNAMES.get(str(pid)); val = base.get(eid, {}).get(nm) if nm else None
                if nm and isinstance(val, (int, float)): pick = (eid, nm, val); break
        if pick: break
    del ed
    if not pick: print('NO_CANDIDATE'); return
    eid, nm, v0 = pick; pool = sorted({d[nm] for d in base.values() if isinstance(d.get(nm), int) and not isinstance(d.get(nm), bool) and d[nm] != v0}) if os.environ.get('POOL') else []      # POOL=1: enum-like parameter, use another value that really occurs on this parameter elsewhere in the project
    if os.environ.get('POOL') and not pool: print('NO_ALTERNATIVE_VALUE'); return
    nv = round(v0 + 0.25, 6) if KIND == 'Double' else pool[0] if pool else int(os.environ['NEWVAL']) if os.environ.get('NEWVAL') else int(v0) % 3 + 1; print('picked 1 element of', cls, 'param', nm, 'old', v0, 'new', nv, flush=True)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); print('open', info.get('open'), str(info.get('error', ''))[:100], flush=True)
        r = await c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': eid, 'param': nm, 'value': nv, 'kind': KIND}); j = await r.json(); print('edit', r.status, str(j.get('error', ''))[:120], flush=True)
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
