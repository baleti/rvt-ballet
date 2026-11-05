"""One process: set_string Comments + in-place SAVE! on FILE (argv1) with value argv2; prints status. Run two at once on the same file to test the save lock. Autodesk samples only."""
import os, sys, asyncio, tempfile, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, val):
    eid = next(e for e, d in rvt_params.params(src).items() if g(d).get('Comments') == '')
    md = tempfile.mkdtemp(); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as cl:
        cl.session._timeout = aiohttp.ClientTimeout(total=None); await cl.get('/api/m/m/saveinfo')
        r = await cl.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': val}); print(val, 'edit', r.status, flush=True)
        if os.environ.get('GO_AT'):
            import time; time.sleep(max(0, float(os.environ['GO_AT']) - time.time()))
        r = await cl.post('/api/m/m/save', json={}); print(val, 'SAVE!', r.status, str((await r.json()).get('error'))[:160], flush=True)
asyncio.run(main(sys.argv[1], sys.argv[2]))
