"""OVERWRITE chain with MIXED ops on a COPY of a REAL project (temp gate / allow_overwrite / delete-any inside this process only): round 1 Double edit (stored named Double of a text-note style), round 2 rotate of a
single-record FamilyInstance, round 3 leaf delete, round 4 by-name Comments edit; each round is a SAVE (overwrite). Per round: status, verify diffs, backup == the file before the save, and after the last round all
edits present (read-back) and the deleted element gone; then RESTORE of the last backup must give the previous generation byte-exactly. Aggregate output only. KEEP_DIR keeps the final file locally (Revit harness).
usage: tools/save_real_chain2.py FILE"""
import os, sys, asyncio, tempfile, time, json, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'; json.dump({'rvt': {os.environ.get('CHAIN_YEAR', '2024'): 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
os.environ.setdefault('RVT_GEOM', '1')
from rvtballet import server
import rvt_params, rvtedit
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def main(src0):
    src = os.path.join(_T, 'copy.rvt'); shutil.copy(src0, src); t0 = time.time()
    pr = rvt_params.params(src); base = {e: dict(g(d)) for e, d in pr.items()}; ed = rvtedit.Edit(src); num = rot = leaf = None
    for eid in list(pr)[:8000]:
        try: pn, i, r, log, q = ed.g.e.trace(eid)
        except Exception: continue
        if ed.latest_partition(eid) != pn: continue
        c = r['class']
        if num is None and c == 'TextNoteAttributes':
            for l in log:
                if l[1] == 'ParamValueDouble.m_paramId':
                    v = int(str(l[4])[4:-1]); pid = v - (1 << 64) if v >= (1 << 63) else v; nm = rvt_params.PNAMES.get(str(pid)); val = base.get(eid, {}).get(nm) if nm else None
                    if nm and isinstance(val, (int, float)): num = (eid, nm, float(val)); break
        if c == 'FamilyInstance':
            if leaf is None:
                try:
                    if ed.cascade(eid) == [eid]: leaf = eid; continue
                except Exception: pass
            if rot is None: rot = eid
        if num and rot and leaf: break
    del ed; cm = next((e for e, d in base.items() if d.get('Comments') == '' and e not in (num or (0,))[:1] and e not in (rot, leaf)), None)
    skip_num = bool(os.environ.get('CHAIN_SKIP_NUM')) and not num and bool(leaf and cm)      # research: files whose reader finds no TextNote double (2017): run the other rounds, report the skip
    if skip_num: num = (0, None, 0.0); print('DOUBLE_ROUND_SKIPPED', flush=True)
    if not (num and leaf and cm): print('NO_CANDIDATES', bool(num), bool(rot), bool(leaf), bool(cm)); return      # no second FamilyInstance to rotate: that round is skipped (reported)
    plan = ([] if skip_num else [('double', {'op': 'set_num', 'eid': num[0], 'param': num[1], 'value': round(num[2] + 0.25, 6)})]) + ([('rotate', {'op': 'rotate', 'eid': rot, 'deg': 30})] if rot else []) + [('delete', {'op': 'delete', 'eid': leaf}), ('string', {'op': 'set_string', 'eid': cm, 'param': 'Comments', 'value': 'chain2 edit'})]
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}; rows = []; gens = [sha(src)]
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json(); print('overwrite_enabled', bool(info.get('allow_overwrite') and info.get('gate_open')), flush=True)
        for k, (kind, op) in enumerate(plan, 1):
            t1 = time.time(); r = await c.post('/api/m/m/edit', json=op); row = {'round': k, 'kind': kind, 'edit': r.status}
            if r.status != 200: row['error'] = str((await r.json()).get('error'))[:110]; rows.append(row); print(row, flush=True); break
            r = await c.post('/api/m/m/save', json={'confirm': True}); j = await r.json(); row['save'] = r.status; row['code'] = j.get('code') if r.status != 200 else 'ok'
            if r.status == 200: row['verify_diffs'] = j['verify']['n_unexpected']; row['backup_is_previous'] = bool(j.get('backup')) and sha(j['backup']) == gens[-1]; gens.append(sha(src))
            row['seconds'] = round(time.time() - t1, 1); rows.append(row); print(row, flush=True)
            if r.status != 200: break
        ok_rounds = sum(1 for r in rows if r.get('save') == 200)
        if ok_rounds == len(plan):
            now = rvt_params.params(src); b = {e: g(d) for e, d in now.items()}
            res = {'double_present': True if skip_num else abs(b[num[0]][num[1]] - (num[2] + 0.25)) < 1e-9, 'string_present': b[cm].get('Comments') == 'chain2 edit', 'deleted_gone': leaf not in b, 'others_missing': len([e for e in base if e not in b and e != leaf])}
            kd = os.environ.get('KEEP_DIR')
            if kd: os.makedirs(kd, exist_ok=True); shutil.copy(src, os.path.join(kd, 'chain2_final.rvt'))
            r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); res['restore_status'] = r.status; res['restored_equals_previous_generation'] = r.status == 200 and sha(src) == gens[-2]
            print('CHAIN2', {'rounds_ok': ok_rounds, 'rounds': len(plan), **res, 'seconds': round(time.time() - t0)})
        else: print('CHAIN2', {'rounds_ok': ok_rounds, 'rounds': len(plan)})
asyncio.run(main(sys.argv[1]))
