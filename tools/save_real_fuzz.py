"""Fuzz on a REAL project through the server API (rvtedit backend): CHAINS random chains of 1-3 by-name string edits (Comments / Mark on random elements that store them empty, sometimes an undo),
SAVE AS with the element-level verify, then a reader read-back: exactly the edited (element, parameter) rows changed. Aggregate output only (no names / ids). Temp files go to $TMPDIR (use a disk path).
usage: tools/save_real_fuzz.py FILE CHAINS SEED OUT.json"""
import os, sys, asyncio, tempfile, time, json, random, collections
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
PARAMS = ('Comments', 'Mark')
TEXTS = ['x', 'Ünï ✓', 'a' * 60, 'quote " and \' end', ' spaced ', 'Mark-001', '0']
async def main(src, n, seed, out):
    rnd = random.Random(seed); pr = rvt_params.params(src); base = {e: dict(g(d)) for e, d in pr.items()}; del pr
    cand = {p: [e for e, d in base.items() if d.get(p) == ''] for p in PARAMS}; stat = collections.Counter(); rows = []
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for k in range(n):
            t0 = time.time()
            while (await (await c.get('/api/m/m/edits')).json())['ops']: await c.post('/api/m/m/edit/undo')
            want = {}; used = set()
            for _ in range(rnd.randint(1, 3)):
                p = rnd.choice(PARAMS); e = rnd.choice(cand[p]); v = rnd.choice(TEXTS)
                if (e, p) in used: continue
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': p, 'value': v}); stat['edit_%d' % r.status] += 1
                if r.status == 200: want[(e, p)] = v; used.add((e, p))
                if rnd.random() < .2 and want:
                    await c.post('/api/m/m/edit/undo'); want.popitem()
            if not want: stat['no_edit'] += 1; continue
            dest = os.path.join(_T, 'o%d.rvt' % k); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json(); stat['save_%d_%s' % (r.status, j.get('code', 'ok'))] += 1
            row = {'chain': k, 'edits': len(want), 'status': r.status, 'seconds': round(time.time() - t0, 1)}
            if r.status == 200:
                now = rvt_params.params(dest); exact = True
                for e in {e for e, _ in want}:
                    a = base[e]; b = g(now.get(e)); ch = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
                    exact &= ch == {p for (ee, p) in want if ee == e} and all(b.get(p) == v for (ee, p), v in want.items() if ee == e)
                row['readback_exact'] = exact; stat['readback_exact' if exact else 'READBACK_MISMATCH'] += 1; os.remove(dest)
            else: row['code'] = j.get('code'); row['n_unexpected'] = (j.get('report') or {}).get('n_unexpected')
            rows.append(row); print(row, flush=True)
    json.dump({'stats': dict(stat), 'rows': rows}, open(out, 'w')); print('REAL-FUZZ', dict(stat))
asyncio.run(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]))
