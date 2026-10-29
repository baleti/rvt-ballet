"""Edit-op fuzz through the server API: random chains of set_string ops (random element, text incl. unicode / empty / long / quotes) on elements that carry
ParamValueAString.m_value, optional undo, then SAVE AS. Every chain must end 200 (verify 0 undeclared) or a classified 4xx; never 500; source untouched.
usage: tools/save_fuzz.py SRC.rvt MODELDIR(sqlite with el table) CHAINS SEED OUT.json   (aggregate output)"""
import os, sys, asyncio, tempfile, hashlib, json, random, time, sqlite3, collections
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
TEXTS = ['', 'x', 'Ünïcödé 日本語 ✓', 'quote " and \' and \\ back', 'a' * 300, ' leading and trailing ', 'line1\nline2', '<b>&amp;</b>', 'Mark-001', '0']
async def main(src, md, n, seed, out):
    from aiohttp.test_utils import TestClient, TestServer
    rnd = random.Random(seed); ids = [r[0] for r in sqlite3.connect(os.path.join(md, 'model.sqlite')).execute("select id from el where cls in ('MaterialElem','PropertySetElement','FamilySymbol') order by id")]
    h0 = sha(src); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}; stat = collections.Counter(); fails = []; t0 = time.time()
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for k in range(n):
            await c.post('/api/m/m/edit/undo')            # reset (ignore 400)
            while (await (await c.get('/api/m/m/edits')).json())['ops']: await c.post('/api/m/m/edit/undo')
            for _ in range(rnd.randint(1, 5)):
                op = {'op': 'set_string', 'eid': rnd.choice(ids), 'value': rnd.choice(TEXTS), 'match': rnd.choice([None, ''])}
                r = await c.post('/api/m/m/edit', json=op); j = await r.json(); stat['edit_%d' % r.status] += 1
                assert r.status != 500, (op, j)
                if rnd.random() < .2: await c.post('/api/m/m/edit/undo')
            d = os.path.join(_T, 'o%d.rvt' % k); r = await c.post('/api/m/m/saveas', json={'dest': d}); j = await r.json(); stat['save_%d_%s' % (r.status, j.get('code', 'ok'))] += 1
            assert sha(src) == h0, 'SOURCE CHANGED'
            if r.status == 200: assert j['verify']['n_unexpected'] == 0; os.remove(d)
            else: fails.append({'chain': k, 'status': r.status, 'code': j.get('code'), 'error': str(j.get('error'))[:200]}); assert r.status != 500 and not os.path.exists(d)
            print(k, r.status, j.get('code', 'ok'), flush=True)
    res = {'chains': n, 'seconds': round(time.time() - t0), 'stats': dict(stat), 'failures': fails}; json.dump(res, open(out, 'w'), indent=1); print(json.dumps({k: v for k, v in res.items() if k != 'failures'}), len(fails), 'non-200 saves')
asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]))
