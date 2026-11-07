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
async def main(src, op, keep):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); row = {}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        md = os.path.join(_T, 'm'); os.makedirs(md); work = os.path.join(_T, 'w.rvt'); shutil.copy(src, work); h0 = sha(work)
        models.m['c0'] = {'dir': md, 'name': 'f', 'src': work}
        info = await (await c.get('/api/m/c0/saveinfo')).json()
        if not info.get('open'): print('NOT_OPEN', info.get('error')); return
        r = await c.post('/api/m/c0/edit', json=op); j = await r.json(); row['edit'] = r.status
        if r.status != 200: row['result'] = 'EDIT_REFUSED ' + str(j.get('error') or j.get('code'))[:120]; print('ONE-EDIT', row); return
        out = os.path.join(_T, 'o.rvt'); t0 = time.time(); r = await c.post('/api/m/c0/saveas', json={'dest': out}); j = await r.json(); row['saveas_s'] = round(time.time() - t0, 1)
        if r.status != 200: row['result'] = 'SAVEAS_REFUSED_%d %s' % (r.status, j.get('code')); row['detail'] = str(j.get('error'))[:200]; print('ONE-EDIT', row); return
        row['verify_diffs'] = j['verify']['n_unexpected']; row.update({k: v for k, v in U.report(work, out).items() if not k.startswith('_')}); bad = []
        r = await c.post('/api/m/c0/save', json={}); j2 = await r.json(); row['save_status'] = r.status
        if r.status == 200:
            if sha(work) != sha(out): bad.append('save!_bytes_differ_from_saveas')
            if not j2.get('backup'): bad.append('no_backup')
            else:
                r = await c.post('/api/m/c0/restore', json={'confirm': True, 'n': 0})
                if r.status != 200 or sha(work) != h0: bad.append('restore_not_original')
        else: row['save_detail'] = str(j2.get('code'))
        shutil.copy(out, keep); row['problems'] = bad; row['result'] = 'OK' if not bad and row['verify_diffs'] == 0 else 'PROBLEM'; print('ONE-EDIT', row)
asyncio.run(main(sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]))
