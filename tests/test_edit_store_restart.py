"""Pending edits survive a viewer restart: stored after /edit, offered by /edits/stored, replayed by /edits/recover; removed after undo-to-empty, SAVE and RESTORE; refused when the file changed. Local sample only (skips without it)."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDITSTORE'] = _T + '/es'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import server, save, editstore
stored = lambda: [f for f in os.listdir(_T + '/es') if f.endswith('.json')] if os.path.isdir(_T + '/es') else []
def mkapp(src):
    md = os.path.join(_T, 'm'); os.makedirs(md, exist_ok=True); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}; return server.make_app(models)
async def run():
    import aiohttp
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); T = aiohttp.ClientTimeout(total=None)
    async with TestClient(TestServer(mkapp(src)), timeout=T) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1490644, 'dx': 2.0}); assert r.status == 200
        assert len(stored()) == 1, stored()
    # "restart": a brand-new app and SaveSessions, same file
    async with TestClient(TestServer(mkapp(src)), timeout=T) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); assert info['pending_edits'] == 0, info
        j = await (await c.get('/api/m/m/edits/stored')).json(); assert j['n'] == 1 and j['usable'], j
        r = await c.post('/api/m/m/edits/recover', json={}); j = await r.json(); assert r.status == 200 and j['recovered'] == 1 and j['n'] == 1, (r.status, j)
        assert (await (await c.get('/api/m/m/saveinfo')).json())['pending_edits'] == 1
        r = await c.post('/api/m/m/edit/undo', json={}); assert r.status == 200 and stored() == [], stored()      # undo to empty removes the store
        await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1490644, 'dx': 1.0}); assert len(stored()) == 1
    # the file changes behind our back: stored edits are refused, kept on disk
    with open(src, 'ab') as f: f.write(b'\0')
    async with TestClient(TestServer(mkapp(src)), timeout=T) as c:
        await c.get('/api/m/m/saveinfo')
        j = await (await c.get('/api/m/m/edits/stored')).json(); assert j['n'] == 0 and j['why'], j
        r = await c.post('/api/m/m/edits/recover', json={}); assert r.status == 409, r.status
        assert len(stored()) == 1, 'a mismatching store must be kept'
    os.truncate(src, os.path.getsize(src) - 1)
    # SAVE removes the store
    async with TestClient(TestServer(mkapp(src)), timeout=T) as c:
        await c.get('/api/m/m/saveinfo'); r = await c.post('/api/m/m/edits/recover', json={}); assert r.status == 200, await r.text()
        r = await c.post('/api/m/m/save', json={}); assert r.status == 200, await r.text(); assert stored() == [], stored()
    print('edit store restart OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
