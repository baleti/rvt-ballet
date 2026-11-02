#!/usr/bin/env python3
"""chain_inplace.py SRC N KEEPDIR: N consecutive in-place SAVE!s (Comments of N different elements) on ONE private copy, a fresh server session per save (like separate app runs); after each: gate ok, edit read back, size, copy kept as KEEPDIR/gK<ext>. Local files only. Use tools via padwrap to test a pad-consume patch."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src0, n, kd):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    ext = os.path.splitext(src0)[1]; work = _T + '/w' + ext; shutil.copy(src0, work); os.makedirs(kd, exist_ok=True)
    els = [e for e, d in rvt_params.params(work).items() if g(d).get('Comments') == '']
    els = els[-n:] if os.environ.get('CHAIN_PICK') == 'last' else els[:n]      # CHAIN_PICK=last: elements late in the list (tail of the partition)
    for k, eid in enumerate(els):
        md = '%s/m%d' % (_T, k); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
        async with TestClient(TestServer(server.make_app(models))) as c:
            c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'chain %d' % k}); assert r.status == 200
            r = await c.post('/api/m/m/save', json={}); j = await r.json()
            print('save', k, r.status, j.get('code'), str(j.get('error') or '')[:120], 'size', os.path.getsize(work), flush=True)
            if r.status != 200: break
        shutil.copy(work, '%s/g%d%s' % (kd, k, ext))
    # all edits readable in the final file
    pr = rvt_params.params(work); print('readback', sum(1 for k, e in enumerate(els) if g(pr[e]).get('Comments') == 'chain %d' % k), 'of', len(els))
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
