"""SAVE (overwrite) + backup + RESTORE on a COPY of a REAL project through the server API (rvtedit backend, temp gate and allow_overwrite set only inside this process; the real gate is never touched):
by-name Comments edit -> SAVE (overwrite) -> backup holds the ORIGINAL bytes, the file changed, the reader shows only Comments changed -> RESTORE -> file byte-identical to the original.
Aggregate output only. usage: tools/save_real_overwrite.py OUT.json FILE"""
import os, sys, asyncio, tempfile, time, json, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(out, src0):
    row = {'size_mb': round(os.path.getsize(src0) / 2 ** 20, 1)}; t0 = time.time(); src = os.path.join(_T, 'copy.rvt'); shutil.copy(src0, src); h0 = sha(src)
    eid = None; row['eid'] = None
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); row['overwrite_enabled'] = bool(info.get('allow_overwrite') and info.get('gate_open'))
        import sqlite3, subprocess
        HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, _T + '/c_src'], capture_output=True, timeout=3600)
        cand = [x[0] for x in sqlite3.connect(_T + '/c_src/model.sqlite').execute("select id from el where cls='FamilyInstance' and bb is not null order by id limit 50")]
        for e in ([int(os.environ['EID'])] if os.environ.get('EID') else cand):
            r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': e, 'dx': 1.0})
            if r.status == 200: eid = e; break
        row['eid'] = eid; assert eid is not None, 'no movable candidate'
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); row['save_status'] = r.status
        if r.status != 200: row['result'] = 'SAVE_%d %s' % (r.status, j.get('code')); row['detail'] = str(j.get('error'))[:160]; row['report_keys'] = sorted((j.get('report') or {}).keys()); row['unexpected_sample'] = str((j.get('report') or {}).get('unexpected', ''))[:600]; print(row); json.dump(row, open(out, 'w')); return
        row['verify_diffs'] = j['verify']['n_unexpected']; row['backup_is_original'] = bool(j.get('backup')) and sha(j['backup']) == h0; row['file_changed'] = sha(src) != h0
        if os.environ.get('KEEP_OUT'): shutil.copy(src, os.environ['KEEP_OUT'])      # keep the in-place SAVE! output (before the restore) for a VM open; local only
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); jr = await r.json(); row['restored_identical'] = r.status == 200 and sha(src) == h0
    row['seconds'] = round(time.time() - t0, 1)
    row['result'] = 'OK' if all([row['overwrite_enabled'], row['verify_diffs'] == 0, row['backup_is_original'], row['file_changed'], row['restored_identical']]) else 'MISMATCH'
    print(row); json.dump(row, open(out, 'w'))
asyncio.run(main(sys.argv[1], sys.argv[2]))
