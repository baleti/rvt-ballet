#!/usr/bin/env python3
"""rvtsave_concurrent.py SRC EID: edit once, fire two in-place SAVE! at the same time; expect exactly one 200, the other refused (busy), file valid, backup == original."""
import os, sys, asyncio, tempfile, shutil, json, hashlib
W = os.path.expanduser('~/rvtsave-work'); _T = tempfile.mkdtemp(dir=W)
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(work, eid):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    md = _T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
    h0 = sha(work)
    async with TestClient(TestServer(server.make_app(models))) as c:
        c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': eid, 'dx': 2.0}); assert r.status == 200, await r.text()
        async def one():
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); return r.status, j
        res = await asyncio.gather(one(), one())
        for st, j in res: print(st, str(j.get('code') or j.get('error') or 'ok')[:160])
        b = [j.get('backup') for st, j in res if st == 200 and j.get('backup')]
        print('ok_count', sum(st == 200 for st, _ in res), 'changed', sha(work) != h0, 'backup_is_original', [sha(x) == h0 for x in b])
src, eid = sys.argv[1:3]; work = _T + '/src.rvt'; shutil.copy(src, work); asyncio.run(run(work, int(eid)))
