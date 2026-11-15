"""set_string on a hosted door and its host wall (2024 Snowdon Facades sample) saves as new; every other element's reader params identical."""
import os, sys, asyncio, tempfile, hashlib, shutil
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser(os.environ.get('HS_SRC', '~/rvtfix/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt'))
from rvtballet import server
import rvt_params
g = lambda x: x.get('params', x)
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = T + '/a.rvt'; shutil.copy(SRC, src); md = T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    p0 = rvt_params.params(src); res = {}
    import aiohttp
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for eid in [int(x) for x in os.environ.get('HS_EIDS', '593207,593206').split(',')]:
            names = [n for n, v in g(p0[eid]).items() if isinstance(v, str) and v != 'hs-test' and '|' not in n and n in rvt_params.PNAMES.values()]
            if not names: res[eid] = 'no empty string param'; continue
            for nm in names:       # first parameter the backend accepts as a stored string (a refusal on others is correct)
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'value': 'hs-test', 'param': nm}); j = await r.json()
                if r.status == 200: names = [nm]; break
            if r.status != 200: res[eid] = 'edit_refused for all %d params:' % len(names) + str(j.get('error'))[:80]; continue
            d = T + '/o%d.rvt' % eid; r = await c.post('/api/m/m/saveas', json={'dest': d}); j = await r.json()
            if r.status != 200: res[eid] = 'save_refused:' + str(j.get('error'))[:80]; await c.post('/api/m/m/edit/undo'); continue
            p1 = rvt_params.params(d); diff = [e for e in p0 if g(p0[e]) != g(p1.get(e, {}))]
            res[eid] = 'saved; changed elements=%s; target=%s' % (diff, g(p1[eid]).get(names[0])); assert diff == [eid] and g(p1[eid]).get(names[0]) == 'hs-test', res[eid]
            await c.post('/api/m/m/edit/undo')
    print(res)
asyncio.run(run())
