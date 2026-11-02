#!/usr/bin/env python3
"""rvtsave_chain.py SRC YEAR OP1 OP2 [OP3 ...] (OP = EID | move:EID | str:EID:PARAM:VALUE | del:EID | num:EID:PARAM:VALUE): two in-place SAVEs in a row on one working copy (OP1, save, OP2, save), then open the result in the Revit VM (audit on)."""
import os, sys, asyncio, tempfile, shutil, json
W = os.path.expanduser('~/rvtsave-work'); _T = tempfile.mkdtemp(dir=W)
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if os.environ.get('RVTSAVE_PADPATCH'):      # scratch experiment: consume the zero pad left by an earlier save (see demo-state/c3x-rvtsave-padconsume.patch.txt); NOT the shared write-lab
    from rvtballet import edit as _ed
    sys.path.insert(0, _ed.WL); import wledit, rvtw
    def _sp(payload, st):
        cap = st.full * rvtw.PAGE_PAYLOAD + getattr(st, 'cap_last', 0)
        if len(payload) < cap: return payload + b'\0' * (cap - len(payload))
        ex = len(payload) - cap
        return payload[:cap] if 0 < ex and payload.endswith(b'\0' * (ex + 4)) else payload
    wledit._shrinkpad = _sp
def op(spec):
    k, *a = str(spec).split(':')      # 'EID' or 'move:EID' = move 2 ft; 'str:EID:PARAM:VALUE' = set_string
    if k == 'num': return {'op': 'set_num', 'eid': int(a[0]), 'param': a[1], 'value': float(a[2])}, int(a[0])
    if k == 'int': return {'op': 'set_num', 'eid': int(a[0]), 'param': a[1], 'value': int(a[2]), 'kind': 'Int'}, int(a[0])
    if k == 'rot': return {'op': 'rotate', 'eid': int(a[0]), 'deg': float(a[1])}, int(a[0])
    if k == 'del': return {'op': 'delete', 'eid': int(a[0])}, int(a[0])
    if k == 'str': return {'op': 'set_string', 'eid': int(a[0]), 'param': a[1], 'value': a[2]}, int(a[0])
    e = int(a[0] if k == 'move' else k); return {'op': 'move', 'eid': e, 'dx': 2.0}, e

async def run(work, ops):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    md = _T + '/m'; os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
    async with TestClient(TestServer(server.make_app(models))) as c:
        c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
        for sp in ops:
            body, e = op(sp)
            r = await c.post('/api/m/m/edit', json=body); assert r.status == 200, await r.text()
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('save', e, r.status, str(j.get('error') or j.get('code') or 'ok')[:200], flush=True)
            if os.environ.get('RVTSAVE_KEEP'): shutil.copy(work, '%s/after_%s.rvt' % (os.environ['RVTSAVE_KEEP'], ops.index(sp) + 1))
            if r.status != 200: return False
    return True
src, year = sys.argv[1:3]; ops = sys.argv[3:]
work = _T + '/src' + os.path.splitext(src)[1].lower(); shutil.copy(src, work)      # keep .rte for templates: Revit rejects an .rte saved under .rvt
if asyncio.run(run(work, ops)) and not os.environ.get('RVTSAVE_NOVM'):
    sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); os.environ['STAGEB'] = '1'
    import stages
    r = stages.api_stage(int(year), work, True, 'rsch%s' % _T[-5:]); print({k: r.get(k) for k in ('ok', 'cmp', 'dialogs', 'err')})
