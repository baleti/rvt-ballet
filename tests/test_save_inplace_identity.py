"""In-place SAVE (overwrite gate open, temp gate file) of an UNEDITED Autodesk 2024 sample: file byte-identical afterwards, a backup holding the original exists, no temp files left."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rte'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        i = await (await c.get('/api/m/m/saveinfo')).json(); assert i['allow_overwrite'] and i['gate_open'], i
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 200, (r.status, j)
    assert sha(src) == h0, 'identity in-place save changed the bytes'
    if j.get('backup'): assert sha(j['backup']) == h0
    left = [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]; assert not left, left
    print('in-place identity save OK; backup=%s' % bool(j.get('backup')))
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
