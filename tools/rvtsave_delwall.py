#!/usr/bin/env python3
"""rvtsave_delwall.py SRC [EID]: try /edit delete (opt-in on) on EID or up to 5 SWall elements, then in-place SAVE! on a copy; print status per step."""
import os, sys, asyncio, tempfile, shutil, json
W = os.path.expanduser('~/rvtsave-work'); _T = tempfile.mkdtemp(dir=W)
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research')]
from savegate import rvt_elements as R
async def run(work):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    walls = [e for e, v in R.elements(open(work, 'rb').read()).items() if v.startswith('SWall|')][:5]; walls = [int(sys.argv[2])] if len(sys.argv) > 2 else walls; print('walls', walls)
    md = _T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for w in walls:
            r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': w}); j = await r.json(); print(w, r.status, str(j.get('code') or j.get('error'))[:200])
            if len(sys.argv) > 2 and r.status == 200:
                r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('save', r.status, str(j.get('code') or j.get('error') or 'ok')[:300])
work = _T + '/src.rvt'; shutil.copy(sys.argv[1], work); asyncio.run(run(work))
