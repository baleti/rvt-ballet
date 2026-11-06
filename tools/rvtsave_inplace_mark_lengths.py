"""(LENGTHS env: comma list of Mark value lengths, one in-place save + restore each) IN-PLACE SAVE! of a Mark string edit on a PRIVATE copy of a real Autodesk .rvt (year gate opened in a temp file), then checks: status, backup == original, only the Mark changed (readback), RESTORE byte-identical. usage: rvtsave_inplace_mark.py SRC.rvt [KEEP.rvt]. Aggregate output only."""
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
    PAR = os.environ.get('PARAM', 'Mark'); CLS = os.environ.get('CLASS')
    c0 = [(e, v['params'].get(PAR)) for e, v in sorted(pr.items()) if e >= 1000 and (v.get('params', {}).get(PAR) is None if os.environ.get('UNSET') else isinstance(v.get('params', {}).get(PAR), str)) and (not CLS or v.get('class') == CLS)]
    res = {'size_mb': round(os.path.getsize(src) / 1e6, 1), 'mark_candidates': len(c0)}
    if not c0: print(res, 'NO_CANDIDATE'); return
    e, old = c0[0]; md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for L in [int(x) for x in os.environ['LENGTHS'].split(',')]:
            val = os.environ.get('VALUE') or ('Q' * L)
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': PAR, 'value': val, 'match': (old or '')}); row = {'L': L, 'edit': r.status}
            if r.status != 200: row['body'] = (await r.text())[:200]; print(row, flush=True); continue
            b0 = sha(src); r = await c.post('/api/m/m/save', json={}, timeout=__import__('aiohttp').ClientTimeout(total=None)); j = await r.json(); row.update(save=r.status, code=j.get('code', 'ok'))
            if r.status == 200:
                pr2 = save._read_params(open(src, 'rb').read()); row['only_target'] = [k for k in pr if pr[k] != pr2.get(k)] == [e] and pr2[e]['params'].get(PAR) == val
                rr = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); row['restored_identical'] = sha(src) == h0
            else: row['untouched'] = sha(src) == b0
            print(row, flush=True)
    print('done', res.get('size_mb')); sys.exit(0)
    print(res, 'OK' if res.get('only_target') and res.get('restored_identical') and res.get('backup_is_original') else 'CHECK')
asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
