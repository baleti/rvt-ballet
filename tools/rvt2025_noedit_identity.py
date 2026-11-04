#!/usr/bin/env python3
"""RESEARCH ONLY: Revit 2025 no-edit SAVE AS with the year gate widened in-process (savegate.adapters.RVT_WRITABLE += 2025; nothing on disk changed).
usage: rvt2025_noedit_identity.py FILE...  -> per file: HTTP status, stream-level diff vs source (count of differing streams / total), output sha, verdict. Outputs in a temp dir, deleted."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')
import atexit; atexit.register(shutil.rmtree, _T, True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import server, save
sg = save._import(); from savegate import adapters; adapters.RVT_WRITABLE = tuple(adapters.RVT_WRITABLE) + ('2025',)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def streams(p):
    from savegate import cfb
    c = cfb.CFB(open(p, 'rb').read()); return {k: hashlib.sha256(v.data).hexdigest() for k, v in c.streams().items()}
async def run(files):
    from aiohttp.test_utils import TestClient, TestServer
    models = server.Models()
    async with TestClient(TestServer(server.make_app(models))) as c:
        for k, f in enumerate(files):
            src = os.path.join(_T, 's%d.rvt' % k); shutil.copy(f, src); h0 = sha(src); md = os.path.join(_T, 'm%d' % k); os.makedirs(md); mid = 'm%d' % k
            models.m[mid] = {'dir': md, 'name': 'a', 'src': src}; out = os.path.join(_T, 'o%d.rvt' % k)
            try:
                await c.get('/api/m/%s/saveinfo' % mid); r = await c.post('/api/m/%s/saveas' % mid, json={'dest': out}); t = (await r.text())[:150].replace('\n', ' ')
                if r.status == 200 and os.path.exists(out):
                    a, b = streams(src), streams(out); d = sorted(x for x in set(a) | set(b) if a.get(x) != b.get(x))
                    v = 'IDENTICAL_BYTES' if sha(out) == h0 else ('STREAMS_EQUAL' if not d else 'DIFF %d/%d %s' % (len(d), len(a), d[:3]))
                else: v = 'REFUSED'
                print(os.path.basename(f)[:2], r.status, v, t if r.status != 200 else '', flush=True)
            except Exception as e: print(os.path.basename(f)[:2], 'EXC', repr(e)[:150], flush=True)
            assert sha(src) == h0
            if os.path.exists(out): os.remove(out)
asyncio.run(run(sys.argv[1:]))
