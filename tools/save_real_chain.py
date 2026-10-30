"""Repeated SAVE (overwrite) cycles on a COPY of a REAL project (temp gate / allow_overwrite inside this process only): N rounds of 'by-name Comments edit on a different element -> SAVE'. Per round: status/code,
verify diffs, layout warning/refusal, size delta, and whether ALL earlier edits are still present (reader read-back). Aggregate output only. usage: tools/save_real_chain.py OUT.json FILE ROUNDS"""
import os, sys, asyncio, tempfile, time, json, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(out, src0, rounds):
    src = os.path.join(_T, 'copy.rvt'); shutil.copy(src0, src); size0 = os.path.getsize(src)
    pr = rvt_params.params(src); cand = [e for e, d in pr.items() if g(d).get('Comments') == ''][:rounds]; rows = []; done = {}
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for k, eid in enumerate(cand, 1):
            t0 = time.time(); val = 'round %d edit' % k
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': val}); row = {'round': k, 'edit_status': r.status}
            if r.status != 200: row['result'] = 'EDIT_REFUSED'; rows.append(row); print(row, flush=True); break
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); row['save_status'] = r.status; row['code'] = j.get('code') if r.status != 200 else 'ok'
            if r.status == 200:
                done[eid] = val; row['verify_diffs'] = j['verify']['n_unexpected']; row['size_delta_vs_start'] = os.path.getsize(src) - size0
                now = rvt_params.params(src); row['earlier_edits_present'] = all(g(now.get(e)).get('Comments') == v for e, v in done.items())
            row['seconds'] = round(time.time() - t0, 1); rows.append(row); print(row, flush=True)
            if r.status != 200: break
    kd = os.environ.get('KEEP_DIR')
    if kd: os.makedirs(kd, exist_ok=True); shutil.copy(src, os.path.join(kd, 'real_chain_final.rvt'))      # local only, for the Revit harness
    json.dump(rows, open(out, 'w')); print('REAL-CHAIN', {'rounds_ok': sum(1 for r in rows if r.get('save_status') == 200), 'rounds': len(rows)})
asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3])))
