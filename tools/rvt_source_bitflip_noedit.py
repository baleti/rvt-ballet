#!/usr/bin/env python3
"""rvt_source_bitflip_noedit.py SRC N SEED : (variant of rvt_source_bitflip.py with NO edit: plain SAVE AS of a flipped source; REFUSED, or the output must read back exactly like the flipped source, else LAUNDER)
Original doc: N times: copy SRC, flip ONE random bit of the SOURCE, set_string Comments on one element + in-place SAVE! through the app server. REFUSED (original must stay byte-identical to the flipped copy) or SAVED: then every other element's params must equal what the flipped source gives (LAUNDER = silent change/loss), the edit must read back. Aggregates and positions only."""
import os, sys, asyncio, tempfile, shutil, json, random, collections
import atexit; _T = tempfile.mkdtemp(); atexit.register(shutil.rmtree, _T, True); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, n, seed):
    R = random.Random(seed); data = open(src, 'rb').read(); ext = os.path.splitext(src)[1]; c = collections.Counter(); bad = []; saved_pos = []
    base = rvt_params.params(src); eid = next(e for e, d in base.items() if g(d).get('Comments') == '')
    for i in range(n):
        dest = None
        work = _T + '/w%d%s' % (i, ext); b = bytearray(data); pos = R.randrange(len(b)); b[pos] ^= 1 << R.randrange(8); open(work, 'wb').write(b); flipped = bytes(b)
        try: ref = rvt_params.params(work)
        except Exception: ref = None
        md = '%s/m%d' % (_T, i); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': work}
        async with TestClient(TestServer(server.make_app(models))) as cl:
            cl.session._timeout = aiohttp.ClientTimeout(total=None)
            try:
                await cl.get('/api/m/m/saveinfo')
                dest = _T + '/o%d%s' % (i, ext); r = await cl.post('/api/m/m/saveas', json={'dest': dest}); st = r.status
            except Exception as e: st = -1
        dest = dest or ''
        cur = open(work, 'rb').read()
        if st != 200:
            c['REFUSED'] += 1
            if cur != flipped: c['ORIG_CHANGED'] += 1; bad.append((i, hex(pos), 'original changed'))
        else:
            c['SAVED'] += 1; saved_pos.append((i, hex(pos), len(data)))
            if os.environ.get('KEEP_DIR') and os.path.exists(dest): os.makedirs(os.environ['KEEP_DIR'], exist_ok=True); shutil.copy(dest, '%s/%s_s%s_i%d%s' % (os.environ['KEEP_DIR'], os.path.basename(src)[:-len(ext)], seed, i, ext))
            try:
                out = rvt_params.params(dest)
                lost = [e for e in (ref or {}) if g(out.get(e, {})) != g(ref[e])] + [e for e in out if ref is not None and e not in ref]
                if lost or ref is None: c['LAUNDER'] += 1; bad.append((i, hex(pos), 'readback/changed %d' % len(lost)))
            except Exception as e: c['LAUNDER'] += 1; bad.append((i, hex(pos), 'output unreadable'))
        os.remove(work)
        if os.path.exists(dest): os.remove(dest)
    print(os.path.basename(src)[:6], 'N', n, dict(c), bad[:8], 'saved_at', saved_pos, flush=True)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
