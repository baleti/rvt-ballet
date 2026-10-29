"""Round-trip identity matrix through the server API: for each file, saveinfo -> saveas (no edits) -> reload the output as a new model -> saveas again;
asserts output == source bytes at both generations and the library verify reports 0 undeclared differences. Aggregate output only.
usage: tools/save_matrix.py OUTJSON FILE [FILE...]   (files: .rvt/.rte; writable years only reach saveas)"""
import os, sys, asyncio, tempfile, hashlib, json, time, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def one(c, models, k, src):
    md = os.path.join(_T, 'm%d' % k); os.makedirs(md); mid = 'f%d' % k; models.m[mid] = {'dir': md, 'name': 'f', 'src': src}
    row = {'size': os.path.getsize(src)}; t0 = time.time()
    info = await (await c.get('/api/m/%s/saveinfo' % mid)).json(); row['version'] = info.get('version'); row['open'] = info.get('open')
    if not info.get('open'): row['result'] = 'REFUSED'; return row
    d1 = os.path.join(_T, 'g1_%d.rvt' % k); r = await c.post('/api/m/%s/saveas' % mid, json={'dest': d1}); j = await r.json()
    if r.status != 200: row['result'] = 'FAIL %s' % j.get('code'); return row
    row['verify_diffs'] = j['verify']['n_unexpected']; row['identical_g1'] = sha(d1) == sha(src)
    md2 = os.path.join(_T, 'n%d' % k); os.makedirs(md2); m2 = 'g%d' % k; models.m[m2] = {'dir': md2, 'name': 'g', 'src': d1}
    i2 = await (await c.get('/api/m/%s/saveinfo' % m2)).json(); d2 = os.path.join(_T, 'g2_%d.rvt' % k)
    j2 = await (await c.post('/api/m/%s/saveas' % m2, json={'dest': d2})).json()
    row['identical_g2'] = bool(j2.get('ok')) and sha(d2) == sha(src); row['version_g1'] = i2.get('version')
    row['seconds'] = round(time.time() - t0, 1)
    row['result'] = 'OK' if row['identical_g1'] and row['identical_g2'] and row['verify_diffs'] == 0 and row['version_g1'] == row['version'] else 'MISMATCH'
    for p in (d1, d2): os.remove(p)
    return row
async def main(out, files):
    from aiohttp.test_utils import TestClient, TestServer
    models = server.Models(); rows = []
    async with TestClient(TestServer(server.make_app(models))) as c:
        for k, f in enumerate(files):
            rows.append(await one(c, models, k, f)); print(k, rows[-1].get('result'), rows[-1].get('version'), rows[-1].get('seconds'), flush=True)
    agg = {'files': len(rows), 'ok': sum(r['result'] == 'OK' for r in rows), 'by_version': {}, 'seconds_total': round(sum(r.get('seconds', 0) for r in rows), 1)}
    for r in rows: v = agg['by_version'].setdefault(str(r.get('version')), {'n': 0, 'ok': 0}); v['n'] += 1; v['ok'] += r['result'] == 'OK'
    json.dump({'aggregate': agg, 'rows': rows}, open(out, 'w'), indent=1); print(json.dumps(agg))
asyncio.run(main(sys.argv[1], sys.argv[2:]))
