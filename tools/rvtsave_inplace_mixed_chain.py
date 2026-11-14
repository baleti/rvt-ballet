"""Mixed-edit in-place chain: Mark then Comments then Mark again on a PRIVATE copy; per save only the target changed; RESTORE n=0,1,2 each step back, last == original. IN-PLACE SAVE! of a Mark string edit on a PRIVATE copy of a real Autodesk .rvt (year gate opened in a temp file), then checks: status, backup == original, only the Mark changed (readback), RESTORE byte-identical. usage: rvtsave_inplace_mark.py SRC.rvt [KEEP.rvt]. Aggregate output only."""
import os, sys, asyncio, tempfile, json, shutil, hashlib, re
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
json.dump({'rvt': {'2024': 'open', '2025': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
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
    import aiohttp
    allp = save._read_params(open(src, 'rb').read()); e2 = next(k for k, v in sorted(allp.items()) if k >= 1000 and k != e and isinstance(v.get('params', {}).get('Comments'), str) and (not (os.environ.get('SAMELEN') or os.environ.get('EMPTYVAL')) or v['params']['Comments']))
    steps = [(e, 'Mark', os.environ.get('MARKVAL', 'chainM1'), old), (e2, 'Comments', (('Z' * len(allp[e2]['params']['Comments'])) if os.environ.get('SAMELEN') else ('' if os.environ.get('EMPTYVAL') else 'chainC1')), allp[e2]['params']['Comments']), (e, 'Mark', 'chainM2', 'chainM1')]
    shas = [h0]
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for i, (eid, p, val, m) in enumerate(steps):
            before = save._read_params(open(src, 'rb').read())
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': p, 'value': val, 'match': m}); row = {'step': i, 'param': p, 'edit': r.status}
            if r.status == 200:
                r = await c.post('/api/m/m/save', json={}, timeout=aiohttp.ClientTimeout(total=None)); j = await r.json(); row.update(save=r.status, code=j.get('code', 'ok')); (r.status != 200) and row.update(err=str(j.get('error'))[:300])
                if r.status != 200 and os.environ.get('UNDO_REFUSED'):
                    u = await c.post('/api/m/m/edit/undo', json={}); row['undo'] = u.status
                if r.status == 200:
                    after = save._read_params(open(src, 'rb').read()); row['only_target'] = [k for k in before if before[k] != after.get(k)] == [eid] and after[eid]['params'][p] == val
                    shas.append(sha(src))
            print(row, flush=True)
        # backups are newest-first and a restore itself adds a backup, so restore the OLDEST chain backup once: must equal the original
        n = len(shas) - 2
        if keep: shutil.copy(src, keep)      # final chained output (before the restore) for a Revit VM open
        rr = await c.post('/api/m/m/restore', json={'n': n, 'confirm': True}); print({'restore_oldest_n': n, 'status': rr.status, 'identical_to_original': sha(src) == h0}, flush=True)
    print('done'); sys.exit(0)
asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
