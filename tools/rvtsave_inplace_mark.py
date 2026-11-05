"""IN-PLACE SAVE! of a Mark string edit on a PRIVATE copy of a real Autodesk .rvt (year gate opened in a temp file), then checks: status, backup == original, only the Mark changed (readback), RESTORE byte-identical. usage: rvtsave_inplace_mark.py SRC.rvt [KEEP.rvt]. Aggregate output only."""
import os, sys, asyncio, tempfile, json, shutil, hashlib, re
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run(orig, keep):
    from rvtballet import save, server
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/p.rvt'; shutil.copy(orig, src); h0 = sha(src)
    pr = save._read_params(open(src, 'rb').read())
    c0 = [(e, v['params']['Mark']) for e, v in sorted(pr.items()) if e >= 1000 and isinstance(v.get('params', {}).get('Mark'), str)]
    res = {'size_mb': round(os.path.getsize(src) / 1e6, 1), 'mark_candidates': len(c0)}
    if not c0: print(res, 'NO_CANDIDATE'); return
    e, old = c0[0]; md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': 'Mark', 'value': 'MKIP', 'match': old}); res['edit'] = r.status
        r = await c.post('/api/m/m/save', json={}, timeout=__import__('aiohttp').ClientTimeout(total=None)); j = await r.json(); res['save'] = r.status; res['code'] = j.get('code', 'ok')
        if r.status != 200:
            res['untouched'] = sha(src) == h0; print(res); return
        res['changed'] = sha(src) != h0
        bl = await (await c.get('/api/m/m/backups')).json(); res['backup_is_original'] = bool(bl) and sha(bl[0]['path']) == h0
        pr2 = save._read_params(open(src, 'rb').read()); diff = [k for k in pr if pr[k] != pr2.get(k)]
        res['params_changed_elems'] = len(diff); res['only_target'] = diff == [e] and pr2[e]['params']['Mark'] == 'MKIP'
        if keep: shutil.copy(src, keep)
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); res['restore_status'] = r.status; res['restored_identical'] = sha(src) == h0
    print(res, 'OK' if res.get('only_target') and res.get('restored_identical') and res.get('backup_is_original') else 'CHECK')
asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
