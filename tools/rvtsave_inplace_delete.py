"""IN-PLACE SAVE! of a DELETE (RVTBALLET_ENABLE_DELETE=1) of one FamilyInstance on a private copy of a real .rvt; reports status, untouched-if-refused, backup==original, restore byte-identical. usage: rvtsave_inplace_delete.py FILE [KEEP_OUT]"""
import os, sys, asyncio, tempfile, json, shutil, hashlib, re
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'2024': 'open', '2025': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(orig, keep):
    from rvtballet import save, server
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/p.rvt'; shutil.copy(orig, src); h0 = sha(src)
    from savegate import rvt_elements as R
    d0 = R.elements(open(src, 'rb').read()); c0 = [e for e, v in sorted(d0.items()) if e > 1000 and v.startswith('FamilyInstance|')]
    res = {'size_mb': round(os.path.getsize(src) / 1e6, 1), 'candidates': len(c0)}
    if not c0: print(res, 'NO_CANDIDATE'); return
    e = int(os.environ['DEL_EID']) if os.environ.get('DEL_EID') else c0[int(os.environ.get('DEL_IDX', '0'))]; res['eid'] = e; md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': e}); res['edit'] = r.status
        if r.status != 200: res['edit_msg'] = (await r.text())[:300]; res['untouched'] = sha(src) == h0; print(res); return
        r = await c.post('/api/m/m/save', json={}, timeout=__import__('aiohttp').ClientTimeout(total=None)); j = await r.json(); res['save'] = r.status; res['code'] = j.get('code', 'ok')
        if r.status != 200:
            res['untouched'] = sha(src) == h0; print(res); return
        res['changed'] = sha(src) != h0
        bl = await (await c.get('/api/m/m/backups')).json(); res['backup_is_original'] = bool(bl) and sha(bl[0]['path']) == h0
        d1 = R.elements(open(src, 'rb').read()); res['target_gone'] = e not in d1; res['others_changed'] = sum(1 for k in d0 if k != e and d0[k] != d1.get(k)); res['count'] = (len(d0), len(d1))
        if keep: shutil.copy(src, keep)
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); res['restore_status'] = r.status; res['restored_identical'] = sha(src) == h0
    print(res, 'OK' if (res.get('target_gone') and res.get('others_changed') == 0) and res.get('restored_identical') and res.get('backup_is_original') else 'CHECK')
asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
