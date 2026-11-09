"""In-place SAVE! of a DELETE of one leaf element on a COPY of a REAL project (rvtedit backend; delete opt-in, overwrite and temp gate set only inside this process).
Checks: gate verify 0 unexpected, backup == original bytes, element gone, no other element changed, RESTORE byte-identical. KEEP_OUT=path keeps the pre-restore output locally for a Revit VM open.
Aggregate output only. usage: tools/save_real_delete_inplace.py OUT.json FILE [CLASS]"""
import os, sys, asyncio, tempfile, time, json, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
import atexit; atexit.register(shutil.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ.setdefault('RVT_GEOM', '1')
from rvtballet import server
import rvt_params, rvtedit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
cls = sys.argv[3] if len(sys.argv) > 3 else 'FamilyInstance'
async def main(out, src0):
    t0 = time.time(); src = os.path.join(_T, 'copy.rvt'); shutil.copy(src0, src); h0 = sha(src); row = {'size_mb': round(os.path.getsize(src) / 2 ** 20, 1), 'class': cls}
    pr = rvt_params.params(src); ed = rvtedit.Edit(src); pick = None
    for eid in list(pr)[:3000]:
        try: pn, i, r, log, q = ed.g.e.trace(eid)
        except Exception: continue
        if r['class'] != cls or ed.latest_partition(eid) != pn: continue
        if os.environ.get('SKIP_VIEW_OWNED') == '1':      # the editor refuses view-owned FamilyInstance (title block etc.); pick a model instance instead
            import re as _re
            if any(l[1] == 'Element.m_ownerDBViewId' and (_re.search(r'(\d+)', str(l[4])) or [0, 0]) and int((_re.search(r'(\d+)', str(l[4])) or _re.search(r'(0)', '0')).group(1)) < 2 ** 62 for l in log): continue
        if os.environ.get('CATID'):      # keep only instances of one category (e.g. -2001330 Structural Columns); header field m_categroryId
            _c = [l for l in log if 'm_categroryId' in str(l[1])]
            if not _c or str(os.environ['CATID']) not in str(_c[0][4]): continue
        try:
            if ed.cascade(eid) == [eid]: pick = eid; break
        except Exception: continue
    del ed
    if not pick: row['result'] = 'NO_CANDIDATE'; print(row); json.dump(row, open(out, 'w')); return
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); row['overwrite_enabled'] = bool(info.get('allow_overwrite') and info.get('gate_open'))
        r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': pick}); j = await r.json(); row['edit_status'] = r.status
        if r.status != 200: row['result'] = 'EDIT_REFUSED'; row['detail'] = str(j.get('error'))[:160]; row['original_untouched'] = sha(src) == h0; print(row); json.dump(row, open(out, 'w')); return
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); row['save_status'] = r.status
        if r.status != 200: row['result'] = 'SAVE_%d %s' % (r.status, j.get('code')); row['detail'] = str(j.get('error'))[:160]; row['original_untouched'] = sha(src) == h0; print(row); json.dump(row, open(out, 'w')); return
        row['verify_diffs'] = j['verify']['n_unexpected']; row['backup_is_original'] = bool(j.get('backup')) and sha(j['backup']) == h0; row['file_changed'] = sha(src) != h0
        b = rvt_params.params(src); row['element_gone'] = pick not in b; row['other_elements_changed'] = len({e for e in pr if e != pick and (e not in b or pr[e] != b[e])})
        if os.environ.get('KEEP_OUT'): shutil.copy(src, os.environ['KEEP_OUT'])
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); row['restored_identical'] = r.status == 200 and sha(src) == h0
    row['seconds'] = round(time.time() - t0, 1)
    row['result'] = 'OK' if all([row['overwrite_enabled'], row['verify_diffs'] == 0, row['backup_is_original'], row['file_changed'], row['element_gone'], row['other_elements_changed'] == 0, row['restored_identical']]) else 'MISMATCH'
    print(row); json.dump(row, open(out, 'w'))
asyncio.run(main(sys.argv[1], sys.argv[2]))
