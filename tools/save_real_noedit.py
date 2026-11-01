"""c4x-rvtmatrix: NO-EDIT load + SAVE AS of real/sample files: output must be byte-identical to the source (or the save refused cleanly). Aggregate output only (size, result, seconds).
usage: tools/save_real_noedit.py OUT.json FILE [FILE...]"""
import os, sys, asyncio, tempfile, time, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def main(out, files):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    rows = []
    for k, src in enumerate(files):
        row = {'size_mb': round(os.path.getsize(src) / 2 ** 20, 1)}; t0 = time.time(); md = os.path.join(_T, 'm%d' % k); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
        async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
            info = await (await c.get('/api/m/m/saveinfo')).json()
            if not info.get('open'): row['result'] = 'NOT_OPEN %s' % str(info.get('error'))[:80]
            else:
                dest = os.path.join(_T, 'o%d.rvt' % k); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json()
                if r.status != 200: row['result'] = 'REFUSED_%d %s' % (r.status, j.get('code'))
                else: row['identical'] = sha(dest) == sha(src); row['verify_diffs'] = j['verify']['n_unexpected']; row['result'] = 'IDENTICAL' if row['identical'] else 'DIFFERS'; os.remove(dest)
        row['seconds'] = round(time.time() - t0, 1); rows.append(row); print(k, row, flush=True)
    json.dump(rows, open(out, 'w'))
asyncio.run(main(sys.argv[1], sys.argv[2:]))
