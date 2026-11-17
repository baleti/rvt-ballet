"""c9x-rvtlink: IN-PLACE SAVE! of a set_link_override edit (opt-in) on a PRIVATE copy of the Autodesk HVAC 2024 sample file ov_A (local): status, backup == original, view record changed only, RESTORE byte-identical. usage: rvtsave_inplace_linkovr.py ov_A.rvt"""
import os, sys, asyncio, tempfile, json, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'; os.environ['RVTBALLET_ENABLE_LINKOVERRIDE'] = '1'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(orig):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    src = _T + '/p.rvt'; shutil.copy(orig, src); h0 = sha(src); res = {}
    md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_link_override', 'eid': 1363877, 'link': 1363937, 'linked_view': 124186}); res['edit'] = r.status
        if r.status != 200: res['err'] = (await r.text())[:300]; print(res); return
        r = await c.post('/api/m/m/save', json={}, timeout=aiohttp.ClientTimeout(total=None)); j = await r.json(); res['save'] = r.status; res['code'] = j.get('code', 'ok')
        if r.status != 200: res['untouched'] = sha(src) == h0; res['error'] = str(j.get('error', ''))[:300]; print(res); return
        res['changed'] = sha(src) != h0; res['size_delta'] = os.path.getsize(src) - os.path.getsize(orig)
        bl = await (await c.get('/api/m/m/backups')).json(); res['backup_is_original'] = bool(bl) and sha(bl[0]['path']) == h0
        shutil.copy(src, _T + '/saved.rvt'); res['saved_copy'] = _T + '/saved.rvt'
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); res['restore'] = r.status; res['restored_identical'] = sha(src) == h0
    print(res, 'OK' if res.get('changed') and res.get('backup_is_original') and res.get('restored_identical') else 'CHECK')
asyncio.run(run(sys.argv[1]))
