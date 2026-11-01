"""[c4x-rvtmatrix: KIND=Double|Int|Bool variant of save_real_overwrite.py: edits one stored NUMERIC named parameter instead of Comments; readback must show only that parameter changed]
SAVE (overwrite) + backup + RESTORE on a COPY of a REAL project through the server API (rvtedit backend, temp gate and allow_overwrite set only inside this process; the real gate is never touched):
by-name Comments edit -> SAVE (overwrite) -> backup holds the ORIGINAL bytes, the file changed, the reader shows only Comments changed -> RESTORE -> file byte-identical to the original.
Aggregate output only. usage: tools/save_real_overwrite.py OUT.json FILE"""
import os, sys, asyncio, tempfile, time, json, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, rvtedit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(out, src0):
    KIND = os.environ.get('KIND', 'Double'); BOOL = KIND == 'Bool'; KIND = 'Int' if BOOL else KIND
    row = {'kind': 'Bool' if BOOL else KIND, 'size_mb': round(os.path.getsize(src0) / 2 ** 20, 1)}; t0 = time.time(); src = os.path.join(_T, 'copy.rvt'); shutil.copy(src0, src); h0 = sha(src)
    pr = rvt_params.params(src); base = {e: dict(g(d)) for e, d in pr.items()}; ed = rvtedit.Edit(src); pick = None
    for eid in list(pr)[:3000]:
        try: pn, i, r, log, q = ed.g.e.trace(eid)
        except Exception: continue
        if ed.latest_partition(eid) != pn: continue
        for l in log:
            if l[1] == 'ParamValue%s.m_paramId' % KIND:
                v = int(str(l[4])[4:-1]); pid = v - (1 << 64) if v >= (1 << 63) else v - (1 << 32) if (1 << 31) <= v < (1 << 32) else v; nm = rvt_params.PNAMES.get(str(pid)); val = base.get(eid, {}).get(nm) if nm else None
                if nm and isinstance(val, (int, float)) and (not BOOL or isinstance(val, bool) or val in (0, 1)) and (BOOL or not isinstance(val, bool)): pick = (eid, nm, val); break
        if pick: break
    del ed
    if not pick: row['result'] = 'NO_CANDIDATE'; print(row); json.dump(row, open(out, 'w')); return
    eid, nm, v0 = pick; nv = (1 - int(v0)) if BOOL else round(v0 + 0.25, 6) if KIND == 'Double' else int(v0) % 3 + 1
    a = base[eid]
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); row['overwrite_enabled'] = bool(info.get('allow_overwrite') and info.get('gate_open'))
        r = await c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': eid, 'param': nm, 'value': nv, 'kind': KIND}); j = await r.json()
        if r.status != 200: row['result'] = 'EDIT_%d %s' % (r.status, str(j.get('error'))[:100]); print(row); json.dump(row, open(out, 'w')); return
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); row['save_status'] = r.status
        if r.status != 200:
            row['result'] = 'SAVE_%d %s' % (r.status, j.get('code')); row['detail'] = str(j.get('error'))[:160]; row['original_untouched'] = sha(src) == h0; print(row); json.dump(row, open(out, 'w')); return
        row['verify_diffs'] = j['verify']['n_unexpected']; row['backup_is_original'] = bool(j.get('backup')) and sha(j['backup']) == h0; row['file_changed'] = sha(src) != h0
        b = g(rvt_params.params(src).get(eid)); row['only_param_changed'] = {k for k in set(a) | set(b) if a.get(k) != b.get(k)} == {nm}; row['value_ok'] = b.get(nm) == nv or (BOOL and bool(b.get(nm)) == bool(nv))
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); jr = await r.json(); row['restored_identical'] = r.status == 200 and sha(src) == h0
    row['seconds'] = round(time.time() - t0, 1)
    row['result'] = 'OK' if all([row['overwrite_enabled'], row['verify_diffs'] == 0, row['backup_is_original'], row['file_changed'], row['only_param_changed'], row['value_ok'], row['restored_identical']]) else 'MISMATCH'
    print(row); json.dump(row, open(out, 'w'))
asyncio.run(main(sys.argv[1], sys.argv[2]))
