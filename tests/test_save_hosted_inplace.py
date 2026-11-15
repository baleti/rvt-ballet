"""set_string on a hosted door and its host wall (2024 Snowdon Facades sample) saves as new; every other element's reader params identical."""
import os, sys, asyncio, tempfile, hashlib, shutil
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['SAVEGATE_BACKUPS'] = T + '/bk'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser(os.environ.get('HS_SRC', '~/rvtfix/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt'))
from rvtballet import server
import rvt_params
import hashlib, json, aiohttp
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
json.dump({'rvt': {'2024': 'open'}}, open(T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
EID = 593207
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = T + '/a.rvt'; shutil.copy(SRC, src); h0 = sha(src); md = T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        p0 = rvt_params.params(src); g = lambda x: x.get('params', x)
        nm = None
        for n, v in g(p0[EID]).items():
            if isinstance(v, str) and '|' not in n and n in rvt_params.PNAMES.values() and (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': EID, 'value': 'hs-inplace', 'param': n})).status == 200: nm = n; break
        assert nm, 'no settable string param on the door'
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('SAVE!', r.status, str(j)[:200]); assert r.status == 200, j
        h1 = sha(src); assert h1 != h0
        p1 = rvt_params.params(src); diff = [e for e in p0 if g(p0[e]) != g(p1.get(e, {}))]; assert diff == [EID] and g(p1[EID])[nm] == 'hs-inplace', diff
        r = await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); j = await r.json(); print('RESTORE', r.status, str(j)[:200]); assert r.status == 200, j
        assert sha(src) == h0, 'restore did not return the original bytes'
    print('hosted door in-place SAVE! ok (only', EID, 'changed), RESTORE byte-identical to original')
asyncio.run(run())
