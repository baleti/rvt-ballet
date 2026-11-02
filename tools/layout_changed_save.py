#!/usr/bin/env python3
"""layout_changed_save.py SRC EID OUT.rvt: private copy of SRC, move element EID +1 ft, in-place SAVE! with RVTBALLET_ALLOW_LAYOUT_CHANGE=1 (set only in this process, temp gate) to produce an output whose page layout changed; copy it to OUT for a Revit VM open. Prints status/verify summary only."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if os.environ.get('LAYOUT_OK', '1') == '1': os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def main(src, eid, out):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    work = _T + '/w.rvt'; shutil.copy(src, work); h0 = sha(work); md = _T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
    async with TestClient(TestServer(server.make_app(models))) as c:
        c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': eid, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}); print('edit', r.status)
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); rep = j.get('report') or j.get('verify') or {}
        print('save', r.status, j.get('code'), str(j.get('error') or '')[:200], 'n_unexpected', rep.get('n_unexpected'), 'changed', sha(work) != h0, 'size', os.path.getsize(work))
        if r.status == 200 and sha(work) != h0: shutil.copy(work, out); print('kept', sha(out)[:6])
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
