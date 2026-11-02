#!/usr/bin/env python3
"""rvtsave_loop.py SRC EID PARAM N [PARALLEL]: N in-place set_string saves of one string parameter, each on a fresh private copy; per iteration ONE json line with the source stat/sha, load-to-save timing, HTTP status, code and the gate's n_unexpected/first unexpected. Built to catch the intermittent 'verify failed: 62 differences' refusal of the hosted scene (c1x-rvtmatrix item 20): a refusal now leaves the evidence (stat, sha, host load) instead of only a count. Aggregate output only."""
import os, sys, asyncio, tempfile, shutil, hashlib, json, time
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def one(k, src, eid, param):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    work = '%s/w%d%s' % (_T, k, os.path.splitext(src)[1]); shutil.copy(src, work); st = os.stat(work); md = '%s/m%d' % (_T, k); os.makedirs(md)
    row = {'i': k, 'eid': eid, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns, 'sha12': sha(work)[:12], 'load1': os.getloadavg()[0]}; t0 = time.time()
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
    async with TestClient(TestServer(server.make_app(models))) as c:
        c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': param, 'value': 'loop %d' % k}); row['edit'] = r.status
        if r.status == 200:
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); row.update(status=r.status, code=j.get('code'), error=str(j.get('error') or '')[:160])
            rep = j.get('report') or {}; row['n_unexpected'] = rep.get('n_unexpected'); row['unexpected'] = (rep.get('unexpected') or [])[:3]
    row['s'] = round(time.time() - t0, 1); row['sha_after12'] = sha(work)[:12]; os.remove(work); shutil.rmtree(md, True); return row
async def main(src, eid, param, n, par):
    sem = asyncio.Semaphore(par); out = []
    async def w(k):
        async with sem: r = await one(k, src, eid, param); print(json.dumps(r), flush=True); out.append(r)
    await asyncio.gather(*[w(k) for k in range(n)])
    bad = [r for r in out if r.get('status') != 200]; print('LOOP', len(out), 'runs', len(bad), 'not saved', flush=True)
a = sys.argv; asyncio.run(main(a[1], int(a[2]), a[3], int(a[4]), int(a[5]) if len(a) > 5 else 1))
