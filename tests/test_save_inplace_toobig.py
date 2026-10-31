"""In-place SAVE! of a big real model when the memory budget is too small: refused up front (507 too_big) BEFORE any edit is replayed or any backup is written; the file is byte-identical, no backup, no temp. Uses the largest local Autodesk 2024/2026 sample and RVTPLAT_MEM_GB=2."""
import os, sys, asyncio, tempfile, shutil, hashlib, json, glob
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = T + '/gate.json'; os.environ['RVTPLAT_MEM_GB'] = '2'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server, save
c = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/202[46]/*.rvt')), key=os.path.getsize)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = T + '/big.rvt'; shutil.copy(c[-1], src); h0 = sha(src); md = T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as cl:
        await cl.get('/api/m/m/saveinfo')
        r = await cl.post('/api/m/m/edit', json={'op': 'move', 'eid': 1365188, 'dx': 1.0}); 
        r = await cl.post('/api/m/m/save', json={}); j = await r.json()
        assert r.status == 507 and j.get('code') == 'too_big', (r.status, j.get('code'), str(j.get('error'))[:120])
    assert sha(src) == h0 and not save.backups(src), 'file touched or backup written by a refused save'
    assert not [f for f in os.listdir(T) if f.endswith(('.tmp', '.part', '.sgtmp'))]
    print('in-place save of a %d MB model under a 2 GB budget: 507 too_big, nothing written' % (os.path.getsize(src) >> 20))
if not c or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
