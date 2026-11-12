"""Same-length string edits, one SAVE AS each (fresh model id per candidate), on N distinct (parameter, element) candidates with a non-empty string value: prints OK / REFUSED(code) per candidate and the refusal rate. Usage: rvtsave_samelen_rate.py src.rvt [N]. Autodesk samples only for public use."""
import os, sys, asyncio, tempfile, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', SAVEGATE_GATE=_T + '/gate.json', RVTBALLET_SNAPSHOT_CACHE='0')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, n):
    base = rvt_params.params(src); seen = set(); cands = []
    for e, d in sorted(base.items()):
        if e < 1000: continue
        for k, v in g(d).items():
            if isinstance(v, str) and v and '|' not in k and k not in seen and len(v) <= 60 and k not in ('Name', 'Type Name', 'Family Name', 'Family and Type'): cands.append((e, k, v)); seen.add(k); break
    cands = cands[:n]; ok = ref = 0
    models = server.Models()
    async with TestClient(TestServer(server.make_app(models))) as cl:
        cl.session._timeout = aiohttp.ClientTimeout(total=None)
        for i, (e, k, v) in enumerate(cands):
            mid = 'm%d' % i; md = tempfile.mkdtemp(dir=_T); models.m[mid] = {'dir': md, 'name': 'a', 'src': src}; await cl.get('/api/m/%s/saveinfo' % mid)
            r = await cl.post('/api/%s/%s/edit' % ('m', mid), json={'op': 'set_string', 'eid': e, 'param': k, 'value': ('Z' * max(1, len(v) + int(os.environ.get('DELTA', '0'))))})
            if r.status != 200: print('EDIT_REFUSED', e, k, len(v), (await r.text())[:100].replace('\n', ' '), flush=True); ref += 1; continue
            out = _T + '/o%d.rvt' % i; r = await cl.post('/api/m/%s/saveas' % mid, json={'dest': out, 'confirm': True}); t = await r.text()
            if r.status == 200: ok += 1; print('OK', e, k, len(v), flush=True)
            else: ref += 1; print('SAVE_REFUSED', r.status, e, k, len(v), t[:140].replace('\n', ' '), flush=True)
            if os.path.exists(out): os.remove(out)
            models.m.pop(mid, None); import gc; gc.collect()      # one model session at a time: otherwise the memory guard (507 too_big) fires from the harness's own retained sessions
    print('ok', ok, 'refused', ref, 'of', len(cands))
asyncio.run(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 20))
