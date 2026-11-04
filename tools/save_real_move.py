"""One MOVE on a REAL project through the server API (rvtedit backend): convert the file, pick a FamilyInstance with a bounding box, move it dx=1 ft, SAVE AS (element-level verify), re-convert the output and check
that ONLY that element's bounding box changed, by exactly (1,0,0) ft. Aggregate output only (no names / ids). KEEP_DIR keeps the edited output locally for the Revit harness.
usage: tools/save_real_move.py OUT.json FILE"""
import os, sys, asyncio, tempfile, time, json, subprocess, sqlite3, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import server
def bbs(d): return {r[0]: json.loads(r[1]) for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select id, bb from el where bb is not null')}
async def main(out, src):
    row = {'size_mb': round(os.path.getsize(src) / 2 ** 20, 1)}; t0 = time.time()
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, _T + '/c_src'], capture_output=True, text=True, timeout=3600); row['convert_ok'] = r.returncode == 0
    if r.returncode: row['result'] = 'CONVERT_FAIL'; print(row); json.dump(row, open(out, 'w')); return
    db = sqlite3.connect(_T + '/c_src/model.sqlite'); cand = [x[0] for x in db.execute("select id from el where cls='FamilyInstance' and bb is not null order by id limit 50")]
    row['candidates'] = len(cand)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json()
        if not info.get('open'): row['result'] = 'NOT_OPEN'; print(row); return
        eid = None
        for e in cand:                        # first instance the writer can move
            r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': e, 'dx': 1.0}); j = await r.json()
            if r.status == 200 and os.environ.get('SKIP_WARNED'):     # research: skip candidates whose edit record mentions a group / design option / host (writer warns on those)
                txt = json.dumps(j) + json.dumps(await (await c.get('/api/m/m/edits')).json())
                if any(k in txt for k in ('hosted on', 'group', 'design option')):
                    await c.post('/api/m/m/edit/undo', json={}); row['skipped_warned'] = row.get('skipped_warned', 0) + 1; continue
            if r.status == 200: eid = e; break
            row.setdefault('refused', []).append(j.get('error', '')[:60])
        if eid is None: row['result'] = 'NO_MOVABLE_CANDIDATE'; row['refused'] = row.get('refused', [])[:3]; print(row); json.dump(row, open(out, 'w')); return
        dest = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json()
        if r.status != 200: row['result'] = 'SAVE_%d %s' % (r.status, j.get('code')); row['n_unexpected'] = (j.get('report') or {}).get('n_unexpected'); print(row); json.dump(row, open(out, 'w')); return
        row['verify_diffs'] = j['verify']['n_unexpected']; row['warnings'] = bool(j.get('warnings')); row['warning_text'] = [str(x)[:140] for x in (j.get('warnings') or [])][:3]
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', dest, _T + '/c_out'], capture_output=True, text=True, timeout=3600)
    a, b = bbs(_T + '/c_src'), bbs(_T + '/c_out'); moved = {i for i in a if i in b and a[i] != b[i]}
    d = [[b[eid][k][x] - a[eid][k][x] for x in range(3)] for k in (0, 1)] if eid in b else None
    alias = {i for i in moved - {eid} if i in a and eid in a and a[i] == a[eid] and i in b and b[i] == b[eid]}      # reader attributes the instance's geometry to its style element (same box before/after): not a second element moving
    row['only_target_moved'] = moved - alias == {eid}
    row['style_alias_boxes'] = len(alias); row['other_boxes_changed'] = len(moved - {eid} - alias); row['shift_ft'] = [round(v, 6) for v in d[0]] if d else None
    row['seconds'] = round(time.time() - t0, 1); row['result'] = 'OK' if row['only_target_moved'] and d and all(abs(d[k][0] - 1) < 1e-6 and abs(d[k][1]) < 1e-6 and abs(d[k][2]) < 1e-6 for k in (0, 1)) and row['verify_diffs'] == 0 else 'MISMATCH'
    kd = os.environ.get('KEEP_DIR')
    if kd: os.makedirs(kd, exist_ok=True); shutil.copy(dest, os.path.join(kd, 'real_moved.rvt'))
    print(row); json.dump(row, open(out, 'w'))
asyncio.run(main(sys.argv[1], sys.argv[2]))
