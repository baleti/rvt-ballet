"""2025 production gate: SAVE AS and in-place SAVE of every local 2025 corpus file are refused with a message and the source stays byte-identical, no temp files, no output. Real gate config untouched (temp journal, overwrite env open)."""
import os, sys, asyncio, tempfile, hashlib, shutil, glob
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/2025/*')))
    for f in fs:
        src = os.path.join(_T, 's.rvt'); shutil.copy(f, src); h0 = sha(src); md = tempfile.mkdtemp(dir=_T)
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/save', json={}); t = await r.text(); assert r.status != 200, 'in-place accepted'; a = t[:90]
            out = os.path.join(_T, 'o.rvt'); r2 = await c.post('/api/m/m/saveas', json={'dest': out}); b = r2.status
            assert not os.path.exists(out) or r2.status == 200
        assert sha(src) == h0, 'source changed'
        assert not [x for x in os.listdir(_T) if x.endswith(('.tmp', '.part'))]
        print(os.path.basename(f)[:2], 'in-place', r.status, 'saveas', b, '|', a.replace('\n', ' '))
        if os.path.exists(out): os.remove(out)
asyncio.run(run())
