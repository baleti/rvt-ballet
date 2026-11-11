"""c6x-rvtmatrix: MANY ops on DIFFERENT element classes in ONE edit session, then ONE in-place SAVE! (private copy, gate opened in a temp dir only). usage: rvt_multi_inplace.py SRC OUT_COPY OPS.json  (OPS.json = list of ops; OUT_COPY = where the saved in-place result is kept for a Revit VM open). Prints per op status, save status, sha change, backup restore check."""
import os, sys, asyncio, tempfile, json, shutil, hashlib, atexit
_T = tempfile.mkdtemp(); atexit.register(shutil.rmtree, _T, True)
os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_SNAPSHOT_CACHE='0')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
_H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(_H, '..'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')]
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(src, out, ops):
    from aiohttp.test_utils import TestClient, TestServer
    work = _T + '/w.rvt'; shutil.copy(src, work); h0 = sha(work); md = _T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
    async with TestClient(TestServer(server.make_app(models))) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); print('open', info.get('open'), str(info.get('error'))[:80])
        bad = 0
        for o in ops:
            r = await c.post('/api/m/m/edit', json=o); j = await r.json(); print('edit', o.get('op'), o.get('eid'), r.status, str(j.get('error') or '')[:100]); bad += r.status != 200
        if bad: print('FAIL: an op was refused'); return 1
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('save', r.status, j.get('ok'), str(j.get('code') or '')[:40], str(j.get('error') or '')[:150])
        if r.status != 200: return 1
        h1 = sha(work); print('bytes changed', h0 != h1, 'size', os.path.getsize(src), '->', os.path.getsize(work))
        shutil.copy(work, out)
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); await r.read(); print('restore', r.status, 'original back byte-exact:', sha(work) == h0)
    return 0
sys.exit(asyncio.run(run(sys.argv[1], sys.argv[2], json.load(open(sys.argv[3])))))
