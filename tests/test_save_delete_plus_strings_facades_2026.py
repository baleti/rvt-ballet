"""c6x-rvtwrite item 146: delete of a hosted window + two set_string (Mark) edits on OTHER elements in one in-place SAVE! (private copy of Autodesk Snowdon Facades 2026). The delete-drift rule used to blame the two edited elements on the delete (422 'delete changed the parameters of 2 surviving element(s)'). Passes when the save is accepted or refused for any other reason; the original must stay intact when refused. Slow (about 25 min)."""
import os, sys, asyncio, tempfile, json, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; json.dump({'rvt': {'2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
import glob; _G = glob.glob(os.path.expanduser('~/rvt-research/corpus/2026/*Facades*.rvt')); ORIG = _G[0] if _G else '/nonexistent'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    src = _T + '/p.rvt'; shutil.copy(ORIG, src); h0 = sha(src); res = {}
    md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    ops = [{'op': 'delete', 'eid': 593207}, {'op': 'set_string', 'eid': 593218, 'param': 'Mark', 'value': 'c6x-a'}, {'op': 'set_string', 'eid': 593221, 'param': 'Mark', 'value': 'c6x-b'}]
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for o in ops:
            r = await c.post('/api/m/m/edit', json=o); res[o['op'] + str(o['eid'])] = r.status
            if r.status != 200: res['err'] = (await r.text())[:200]; assert sha(src) == h0; print(res, 'EDIT-REFUSED original intact'); return
        r = await c.post('/api/m/m/save', json={}, timeout=aiohttp.ClientTimeout(total=None)); j = await r.json(); res['save'] = r.status
        if r.status != 200:
            assert sha(src) == h0, 'refused but original changed'; res['error'] = str(j.get('error', ''))[:300]; assert 'delete changed the parameters of' not in res['error'], res; print(res, 'SAVE-REFUSED original intact'); return
        assert sha(src) != h0
        bl = await (await c.get('/api/m/m/backups')).json(); assert bl and sha(bl[0]['path']) == h0, 'backup != original'
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); assert sha(src) == h0, 'restore not identical'
    print(res, 'ACCEPTED, backup==original, restore identical')
if not os.path.exists(ORIG): print('skip'); sys.exit(0)
asyncio.run(run())
