"""UPDATED 2026-11-06 (c3x-rvtsave): the writer now consumes its zero pad, so the second-generation case below no longer changes the layout; the layout_changed guard itself is still in save.py (documented by test_save_chain10 / refusal tests).
Second-generation edit (editing a file the writer already rewrote) re-pages the partition stream (full pages 72->73, last-page capacity 25704->0, +36864 B) and is NOT confirmed to open in Revit
(gen4/gen8 of the chain were unreachable in the VM). SAVE AS must carry a warning, overwrite must be refused (409 layout_changed) unless RVTBALLET_ALLOW_LAYOUT_CHANGE=1; a first-generation edit of the
Revit-written original keeps the layout: no warning. The gen-1 file is produced here by the viewer itself.
VM VERDICT (2026-11-02, c4x-rvtmatrix items 23/24, CORRECTED): a layout-changed in-place output (move, 2024 cols2 and 2026 anno1 scenes, override on) OPENS in Revit 2024/2026 offline VM (revit_open=True cmp 0/0, no dialogs) when the file keeps its .rte extension. An earlier "rejected" verdict was a test artifact (these scenes are templates; renamed .rvt Revit says not a valid .rvt, unedited controls too). Refusal stays default because the layout is not otherwise proven.
"""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
EDIT = {'op': 'set_string', 'field': 'ParamValueAString.m_value', 'value': 'again-é', 'match': ''}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    async def session(src, mid):
        md = os.path.join(_T, 'm' + mid); os.makedirs(md); models = server.Models(); models.m[mid] = {'dir': md, 'name': 'a', 'src': src}; return models
    g0 = os.path.join(_T, 'gen0.rvt'); shutil.copy(RTE, g0); g1 = os.path.join(_T, 'gen1.rvt'); g2 = os.path.join(_T, 'gen2.rvt')
    async with TestClient(TestServer(server.make_app(await session(g0, 'a')))) as c:
        await c.get('/api/m/a/saveinfo'); await c.post('/api/m/a/edit', json=dict(EDIT, eid=24))
        j = await (await c.post('/api/m/a/saveas', json={'dest': g1})).json(); assert j['ok'] and 'warnings' not in j, j          # generation 1: layout kept, no warning
    async with TestClient(TestServer(server.make_app(await session(g1, 'b')))) as c:
        await c.get('/api/m/b/saveinfo'); await c.post('/api/m/b/edit', json=dict(EDIT, eid=25)); h1 = sha(g1)
        j = await (await c.post('/api/m/b/saveas', json={'dest': g2})).json(); assert j['ok'] and 'warnings' not in j, j     # generation 2: since rvt-research 8f7719a the re-saved partition consumes its own zero pad, layout kept, no warning
        r = await c.post('/api/m/b/save', json={}); j = await r.json(); assert r.status == 200 and sha(g1) == sha(g2), (r.status, j)  # overwrite of a layout-keeping edit works and equals SAVE AS
    print('save layout OK (gen1 and gen2 keep the layout: no warning, overwrite == SAVE AS)')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
