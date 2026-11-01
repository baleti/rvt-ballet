#!/usr/bin/env python3
"""rvtwrite2_refuse_sweep.py DIR...: for every .rvt in the dirs (2016-2023 files), in-place SAVE with the overwrite gate OPEN and SAVE AS through the app: both must be refused
with a 'writable years' message, the source bytes unchanged, no temp/backup leftovers. Prints one line per file (sha8, year dir, verdict) and a total. Local files only."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, glob
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {y: 'open' for y in map(str, range(2015, 2028))}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def one(c, models, f, k):
    src = os.path.join(_T, 'src%d.rvt' % k); shutil.copy(f, src); h0 = sha(src); md = os.path.join(_T, 'm%d' % k); os.makedirs(md)
    mid = 'm%d' % k; models.m[mid] = {'dir': md, 'name': 'a', 'src': src}
    await c.get('/api/m/%s/saveinfo' % mid)
    r = await c.post('/api/m/%s/save' % mid, json={}); t = await r.text(); ok = r.status != 200 and ('writable years' in t or 'unsupported_version' in t)
    out = os.path.join(_T, 'o%d.rvt' % k); r2 = await c.post('/api/m/%s/saveas' % mid, json={'dest': out}); t2 = await r2.text()
    ok2 = r2.status != 200 and not os.path.exists(out)
    left = [x for x in os.listdir(_T) if x.endswith(('.tmp', '.part', '.bak'))]
    same = sha(src) == h0
    return ok, ok2, same, not left, t[:80] if not ok else ''
async def run(files):
    from aiohttp.test_utils import TestClient, TestServer
    models = server.Models(); bad = 0
    async with TestClient(TestServer(server.make_app(models))) as c:
        for k, f in enumerate(files):
            try: res = await one(c, models, f, k)
            except Exception as e: res = (False, False, False, False, repr(e)[:80])
            v = 'REFUSED_CLEAN' if all(res[:4]) else 'FAIL'
            bad += v == 'FAIL'
            print(hashlib.sha256(open(f, 'rb').read()).hexdigest()[:6], os.path.basename(os.path.dirname(f)), v, res[:4], res[4], flush=True)
    print('TOTAL', len(files), 'bad', bad)
files = sorted(f for d in sys.argv[1:] for f in glob.glob(d + '/*.rvt'))
if save.SaveSessions().available: asyncio.run(run(files))
else: print('skip')
