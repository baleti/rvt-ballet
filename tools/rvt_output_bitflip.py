#!/usr/bin/env python3
"""rvt_output_bitflip.py (derived): save once clean, then flip ONE bit of the SAVED OUTPUT, edit+SAVE! again; refused (file untouched) or saved with no laundering.
(orig doc) rvt_source_bitflip.py SRC N SEED : N times: copy SRC, flip ONE random bit of the SOURCE, set_string Comments on one element + in-place SAVE! through the app server. REFUSED (original must stay byte-identical to the flipped copy) or SAVED: then every other element's params must equal what the flipped source gives (LAUNDER = silent change/loss), the edit must read back. Aggregates and positions only."""
import os, sys, asyncio, tempfile, shutil, json, random, collections
import atexit; _T = tempfile.mkdtemp(); atexit.register(shutil.rmtree, _T, True); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
PARAM = os.environ.get('PARAM', 'Comments')
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, n, seed):
    R = random.Random(seed); data = open(src, 'rb').read(); ext = os.path.splitext(src)[1]; c = collections.Counter(); bad = []; savedpos = []
    base = rvt_params.params(src); eid = next(e for e, d in base.items() if g(d).get(PARAM, None) is not None and (g(d).get(PARAM) == '' or os.environ.get('PARAM')))
    for i in range(n):
        work = _T + '/w%d%s' % (i, ext); open(work, 'wb').write(data)
        md = '%s/m%d' % (_T, i); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
        async with TestClient(TestServer(server.make_app(models))) as cl:
            cl.session._timeout = aiohttp.ClientTimeout(total=None)
            await cl.get('/api/m/m/saveinfo')
            r = await cl.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': PARAM, 'value': 'first %d' % i}); r1 = r.status
            if r1 == 200: r = await cl.post('/api/m/m/save', json={}); r1 = r.status
        if r1 != 200: c['FIRST_SAVE_FAILED'] += 1; os.remove(work); continue
        b = bytearray(open(work, 'rb').read()); pos = R.randrange(len(b)); b[pos] ^= 1 << R.randrange(8); open(work, 'wb').write(b); flipped = bytes(b)
        try: ref = rvt_params.params(work)
        except Exception: ref = None
        md = '%s/n%d' % (_T, i); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
        async with TestClient(TestServer(server.make_app(models))) as cl:
            cl.session._timeout = aiohttp.ClientTimeout(total=None)
            try:
                await cl.get('/api/m/m/saveinfo')
                r = await cl.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': PARAM, 'value': 'second %d' % i}); st = r.status
                if st == 200: r = await cl.post('/api/m/m/save', json={}); st = r.status
            except Exception as e: st = -1
        cur = open(work, 'rb').read()
        if st != 200:
            c['REFUSED'] += 1
            if cur != flipped: c['ORIG_CHANGED'] += 1; bad.append((i, hex(pos), 'original changed'))
        else:
            c['SAVED'] += 1; savedpos.append(pos)
            try:
                out = rvt_params.params(work)
                lost = [e for e in (ref or {}) if e != eid and g(out.get(e, {})) != g(ref[e])]
                if g(out.get(eid, {})).get('Comments') != 'second %d' % i or lost or ref is None: c['LAUNDER'] += 1; bad.append((i, hex(pos), 'readback/changed %d' % len(lost)))
            except Exception as e: c['LAUNDER'] += 1; bad.append((i, hex(pos), 'output unreadable'))
        os.remove(work)
    print(os.path.basename(src)[:6], 'N', n, dict(c), bad[:8], 'saved_pos', savedpos[:8], flush=True)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
