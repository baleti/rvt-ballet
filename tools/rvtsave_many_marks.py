#!/usr/bin/env python3
"""rvtsave_many_marks.py SRC OUT [N] : N set_string Mark edits (one 100 KB value, one empty value, rest 'm<i>') in ONE gated SAVE AS through the app server; read-back of every edit and a check that no other element/param changed. Gate widened for research on any year. Aggregates only."""
import os, sys, asyncio, tempfile, shutil, json
import atexit; _T = tempfile.mkdtemp(); atexit.register(shutil.rmtree, _T, True)
os.environ.update(RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, out, n):
    base = rvt_params.params(src); eids = [e for e, d in base.items() if isinstance(g(d).get('Mark'), str)][:n]
    want = {}
    VALS = json.loads(os.environ['VALUES']) if os.environ.get('VALUES') else None      # VALUES='["a","b"]': exact values for the first len() Marks
    for i, e in enumerate(eids): want[e] = VALS[i] if VALS else ('x' * 4000 if i == 1 else ('' if i == 2 else 'm%d' % i))
    md = _T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as cl:
        cl.session._timeout = aiohttp.ClientTimeout(total=None)
        await cl.get('/api/m/m/saveinfo'); bad = 0
        import time; t0 = time.time()
        for k, (e, v) in enumerate(want.items()):
            if k % 20 == 0: print('edit', k, '%.0fs' % (time.time() - t0), flush=True)
            r = await cl.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': 'Mark', 'value': v})
            if r.status != 200: bad += 1; print('edit refused', e, r.status, (await r.text())[:100])
        if INPLACE: r = await cl.post('/api/m/m/save', json={'confirm': True}); t = await r.text(); print('save in place', r.status, t[:200]); out = src
        else: r = await cl.post('/api/m/m/saveas', json={'dest': out, 'confirm': True}); t = await r.text(); print('saveas', r.status, t[:200])
    res = rvt_params.params(out)
    wrong = [e for e, v in want.items() if g(res.get(e, {})).get('Mark') != v]
    other = [e for e in base if e not in want and g(res.get(e, {})) != g(base[e])]
    print('edits', len(want), 'edit_refused', bad, 'readback_wrong', len(wrong), 'other_elements_changed', len(other), 'missing', len([e for e in base if e not in res]))
INPLACE = bool(os.environ.get('INPLACE'))
asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 600))
