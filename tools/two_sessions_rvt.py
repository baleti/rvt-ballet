#!/usr/bin/env python3
"""two_sessions_rvt.py SRC.rfa|rvt : two rvt-ballet app sessions load ONE private copy; A edits Comments of element 1 and SAVE!s (200); B (stale) edits element 2 and SAVE!s: must be refused (409, A's bytes unchanged); a fresh B session then saves element 2 (200) and both edits read back. Exit 1 on any ESCAPE."""
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
async def session(work, tag):
    md = '%s/m%s' % (_T, tag); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
    c = TestClient(TestServer(server.make_app(models))); await c.start_server(); c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo'); return c
async def edit_save(c, eid, val):
    r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': val}); assert r.status == 200, await r.text()
    r = await c.post('/api/m/m/save', json={}); return r.status, await r.json()
async def main(src0):
    ext = os.path.splitext(src0)[1]; work = _T + '/w' + ext; shutil.copy(src0, work); bad = 0
    els = [e for e, d in rvt_params.params(work).items() if g(d).get('Comments') == '']
    e1, e2 = els[0], els[1]
    a = await session(work, 'a'); b = await session(work, 'b')
    s, j = await edit_save(a, e1, 'sessionA'); print('A save', s, flush=True); bad += s != 200; after_a = sha(work)
    s, j = await edit_save(b, e2, 'sessionB'); print('B stale save', s, str(j.get('code') or j.get('error'))[:100], flush=True)
    kept = sha(work) == after_a; print('A bytes kept', kept); bad += (s == 200) or not kept
    await a.close(); await b.close()
    b2 = await session(work, 'b2'); s, j = await edit_save(b2, e2, 'sessionB'); j = j or {}; print('B fresh save', s, str(j.get('code') or j.get('error'))[:300], flush=True); bad += s != 200; await b2.close()
    pr = rvt_params.params(work); ok = g(pr[e1]).get('Comments') == 'sessionA' and g(pr[e2]).get('Comments') == 'sessionB'; print('both edits read back', ok); bad += not ok
    shutil.copy(work, os.environ.get('KEEP', _T + '/final') + ext); print('problems', bad); sys.exit(1 if bad else 0)
asyncio.run(main(sys.argv[1]))
