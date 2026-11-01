#!/usr/bin/env python3
"""rvtgap_text.py SRC: set_string Comments on the first candidate FamilyInstance with many tricky values (accents, CJK, RTL, empty, 4096 chars, NUL, newline, lone surrogate, trailing space), SAVE AS each, re-read the parameter from the output and compare. Prints one line per value: accepted/refused and read-back equality (ESCAPE = accepted but read-back differs)."""
import sys, os, asyncio, shutil, importlib.util, json
spec = importlib.util.spec_from_file_location('o', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rvtsave_oracle.py')); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
VALS = ['Ünïcödé', '日本語', 'שלום עולם', '', 'x' * 4096, 'a\x00b', 'line1\nline2', 'lone\ud800surrogate', 'trail  ', ' lead', 'tab\there', '​zero-width', 'écombining', '<>&"\'', '﻿bom']
async def one(src, eid, val):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    md = o._T + '/m'; shutil.rmtree(md, ignore_errors=True); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': val})
        if r.status != 200: return 'refused-edit', (await r.text())[:80]
        out = o._T + '/out.rvt'; r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        if r.status != 200: return 'refused-save', str(j.get('error'))[:80]
        from rvtballet import save
        got = save._read_params(open(out, 'rb').read())
        return 'saved', got.get(eid, got) if isinstance(got, dict) else got
src = sys.argv[1]; w = o._T + '/src.rvt'; shutil.copy(src, w); eid = o.pick(w)
for cand in o.CANDS[:40]:
    st, d = asyncio.run(one(w, cand, 'probe'))
    if st != 'refused-edit': eid = cand; break
print('eid', eid)
for v in VALS:
    try: st, d = asyncio.run(one(w, eid, v))
    except BaseException as e: st, d = 'EXC', '%s %s' % (type(e).__name__, str(e)[:80])
    ok = ''
    if st == 'saved': ok = 'READBACK_EQUAL' if (isinstance(d, dict) and d.get('Comments') == v) or d == v or (isinstance(d, str) and v in d) else 'READBACK_DIFF'
    print(repr(v[:14]), len(v), st, ok, str(d)[:100].replace('\n', ' '))
