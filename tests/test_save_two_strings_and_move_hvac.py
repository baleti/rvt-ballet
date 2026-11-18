"""c6x-rvtwrite item 33: two set_string (Mark) edits on two elements plus a move of a third, one in-place SAVE! on a private copy of the Autodesk HVAC 2024 sample (ov_A, local; skips if absent). Accepted with all three applied and backup == original + restore identical, or refused with the original intact."""
import os, sys, asyncio, tempfile, json, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
ORIG = os.path.expanduser('~/c9x-rvtlink-work/ovrp2024/ov_A.rvt')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    src = _T + '/p.rvt'; shutil.copy(ORIG, src); h0 = sha(src); res = {}
    md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    ops = [{'op': 'set_string', 'eid': 1365188, 'param': 'Mark', 'value': 'c6x-a'}, {'op': 'set_string', 'eid': 1366142, 'param': 'Mark', 'value': 'c6x-b'}, {'op': 'move', 'eid': 1366299, 'dx': 0.5, 'dy': 0.0, 'dz': 0.0}]
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for o in ops:
            r = await c.post('/api/m/m/edit', json=o); res[o['op'] + str(o['eid'])] = r.status
            if r.status != 200: res['err'] = (await r.text())[:200]; assert sha(src) == h0; print(res, 'EDIT-REFUSED original intact'); return
        r = await c.post('/api/m/m/save', json={}, timeout=aiohttp.ClientTimeout(total=None)); j = await r.json(); res['save'] = r.status
        if r.status != 200:
            assert sha(src) == h0, 'refused but original changed'; res['error'] = str(j.get('error', ''))[:300]; print(res, 'SAVE-REFUSED original intact'); return
        assert sha(src) != h0
        bl = await (await c.get('/api/m/m/backups')).json(); assert bl and sha(bl[0]['path']) == h0, 'backup != original'
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); assert sha(src) == h0, 'restore not identical'
    print(res, 'ACCEPTED, backup==original, restore identical')
if not os.path.exists(ORIG): print('skip'); sys.exit(0)
asyncio.run(run())
