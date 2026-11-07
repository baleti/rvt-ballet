"""In-place move of an SWall (Autodesk Structural 2024 sample, local copy) is refused by the savegate span rule
(the wall move touches ~74 small runs over ~56 KB, the rule allows 2048 B for one move): 409/422 refusal, source sha unchanged, no temp leftovers.
With RVTBALLET_SPAN_RULE=0 the same save is accepted (experiment only, not Revit-VM judged here). Skipped when the sample is absent."""
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path[:0] = [os.path.expanduser('~/src/savegate'), HERE]
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt'); E = 585174      # a wall that hosts nothing (585072 hosts 10 elements and is now refused earlier by the hosted-elements guard)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
from rvtballet import server, save
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/a.rvt'; shutil.copy(F, src); h0 = sha(src); md = _T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': E, 'dx': 2.0}); assert r.status == 200, await r.text()
        r = await c.post('/api/m/m/save', json={}); j = await r.json()
        assert r.status >= 400 and 'member_span' in json.dumps(j), (r.status, j)
        assert sha(src) == h0 and not [f for f in os.listdir(_T) if 'sgtmp' in f or f.endswith('.part')], 'source changed or temp left'
    print('wall move span refusal OK: refused', r.status, 'source untouched')
if not os.path.exists(F) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
