"""One by-NAME string edit on a REAL project through the server API (rvtedit backend): pick an element that stores an EMPTY 'Comments' parameter, edit it, SAVE AS (element-level verify), read the parameter
back from the output with the reader and check that it is the only parameter of that element that changed. Prints aggregate results only (no file names, ids or element names).
usage: tools/save_real_edit.py OUT.json FILE [FILE...]"""
import os, sys, asyncio, tempfile, time, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def one(c, models, k, src):
    row = {'size_mb': round(os.path.getsize(src) / 2 ** 20, 1)}; t0 = time.time()
    pr = rvt_params.params(src); cand = [e for e, d in pr.items() if (bool(g(d).get('Comments')) if os.environ.get('RVT_EDIT_NONEMPTY') else g(d).get('Comments') == '')]      # RVT_EDIT_NONEMPTY: pick an element whose Comments is really stored
    row['candidates'] = len(cand)
    if not cand: row['result'] = 'NO_CANDIDATE'; return row
    eid = cand[0]; md = os.path.join(_T, 'm%d' % k); os.makedirs(md); mid = 'f%d' % k; models.m[mid] = {'dir': md, 'name': 'f', 'src': src}
    info = await (await c.get('/api/m/%s/saveinfo' % mid)).json()
    if not info.get('open'): row['result'] = 'NOT_OPEN ' + str(info.get('error'))[:80]; return row
    r = await c.post('/api/m/%s/edit' % mid, json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': os.environ.get('RVT_EDIT_VALUE', 'edited by h2-viewer test')}); j = await r.json()
    if r.status != 200: row['result'] = 'EDIT_REFUSED %s' % j.get('error', '')[:100]; return row
    out = os.path.join(_T, 'o%d.rvt' % k); keep = os.environ.get('RVT_KEEP_DIR'); r = await c.post('/api/m/%s/saveas' % mid, json={'dest': out}); j = await r.json(); keep and r.status == 200 and __import__('shutil').copy(out, os.path.join(keep, 'k%d_%s.rvt' % (k, os.path.basename(src)[:6].replace(' ', '_'))))
    if r.status != 200: row['result'] = 'SAVE_%d %s' % (r.status, j.get('code')); row['detail'] = str(j.get('error'))[:160]; row['n_unexpected'] = (j.get('report') or {}).get('n_unexpected'); return row
    row['verify_diffs'] = j['verify']['n_unexpected']; row['warnings'] = bool(j.get('warnings'))
    b = g(rvt_params.params(out).get(eid)); a = g(pr.get(eid)); changed = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
    row['only_comments_changed'] = changed == {'Comments'} and b.get('Comments') == os.environ.get('RVT_EDIT_VALUE', 'edited by h2-viewer test')
    row['seconds'] = round(time.time() - t0, 1); row['result'] = 'OK' if row['only_comments_changed'] and row['verify_diffs'] == 0 else 'MISMATCH'
    kd = os.environ.get('KEEP_DIR')
    if kd: import shutil; os.makedirs(kd, exist_ok=True); shutil.copy(out, os.path.join(kd, 'real%d_edited.rvt' % k))      # local only, for the Revit harness
    os.remove(out); return row
async def main(out, files):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); rows = []
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        for k, f in enumerate(files):
            rows.append(await one(c, models, k, f)); print(k, rows[-1], flush=True)
    json.dump(rows, open(out, 'w'), indent=1); print('REAL-EDIT', {'files': len(rows), 'ok': sum(r['result'] == 'OK' for r in rows)})
asyncio.run(main(sys.argv[1], sys.argv[2:]))
