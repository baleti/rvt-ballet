"""Lean one-edit pass (c3x-rvtread): apply ONE known edit op through the rvt-ballet server API, SAVE AS (element-level verify), SAVE! in place on a private copy, restore the backup and check the original sha.
Unlike rvt_class_pass.py it does NOT parse every element's parameters (that scan needs > 28 GB on a 24 MB Structural file), so it fits next to the VMs.  Aggregate output only; Autodesk samples / synthetic only.
usage: tools/rvt_one_edit.py FILE 'OPJSON' KEEP_OUT.rvt     e.g. '{"op":"set_string","eid":329,"field":"DatumPlane.m_text","value":"X c3x","match":"X","param":null}'"""
import os, sys, asyncio, tempfile, time, json, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit; atexit.register(shutil.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc'); os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
_H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(_H, '..')); sys.path.insert(0, _H)
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
from rvtballet import server
import rvt_untouched_report as U
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def main(src, ops, keep):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); row = {'steps': []}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        md = os.path.join(_T, 'm'); os.makedirs(md); work = os.path.join(_T, 'w.rvt'); shutil.copy(src, work); hs = [sha(work)]
        models.m['c0'] = {'dir': md, 'name': 'f', 'src': work}
        info = await (await c.get('/api/m/c0/saveinfo')).json()
        if not info.get('open'): print('NOT_OPEN', info.get('error')); return
        for o in ops:
            r = await c.post('/api/m/c0/edit', json=o); j = await r.json()
            if r.status != 200: row['steps'].append('edit_%d' % r.status); break
            if os.environ.get('CHAIN_SAVEAS_FIRST'):
                rr = await c.post('/api/m/c0/saveas', json={'dest': os.path.join(_T, 'sa%d.rvt' % len(hs))}); row['steps'].append('saveas_%d' % rr.status)
            r = await c.post('/api/m/c0/save', json={}); j = await r.json()
            row['steps'].append('save_%d%s' % (r.status, '' if r.status == 200 else ' ' + str(j.get('code')) + ' ' + str(j.get('error'))[:300]))
            if r.status != 200: break
            hs.append(sha(work))
        row['distinct_states'] = len(set(hs)) == len(hs)
        shutil.copy(work, keep)
        for i in range(len(hs) - 1):
            r = await c.post('/api/m/c0/restore', json={'confirm': True, 'n': 0}); row['steps'].append('restore_%d' % r.status)
            row.setdefault('after_restore_matches_state', []).append(hs.index(sha(work)) if sha(work) in hs else -1)
        if os.environ.get('CHAIN_RESTORE_OLDEST'):
            bl = await (await c.get('/api/m/c0/backups')).json(); nb = len(bl) if isinstance(bl, list) else len(bl.get('backups', []))
            r = await c.post('/api/m/c0/restore', json={'confirm': True, 'n': nb - 1}); row['steps'].append('restore_oldest_%d_of_%d' % (r.status, nb))
            row['oldest_restore_is_original'] = sha(work) == hs[0]
        row['final_is_original'] = sha(work) == hs[0]
        print('TWO-SAVE', row)
asyncio.run(main(sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]))
