"""Edit coverage by element class for in-place save (c3x-rvtmatrix). For every requested class of a project: pick up to 3 elements (set_string / set_num / move), apply them through the
rvt-ballet server API in ONE session, SAVE AS (element-level verify), then SAVE! in place on a private copy (gate opened in a temp file only), and check:
  verify n_unexpected == 0 / honest refusal; re-read params: only the declared params changed; SAVE! bytes == SAVE AS bytes; backup restores the original sha256; untouched elements % (tools/rvt_untouched_report).
Aggregate output only (class names, counts, percentages; no element names or paths).   usage (one fresh process per class unless RVT_CP_INPROC=1, memory released per class): tools/rvt_class_pass.py OUT.json FILE CLASS[,CLASS...]|ALL   (env KEEP_DIR=dir [KEEP_TAG=tag] keeps each SAVE AS output for Revit VM opens)"""
import os, sys, asyncio, tempfile, time, json, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit, shutil as _sh; atexit.register(_sh.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')      # temp dir and ALL caches die with the process (host disk emergency 2026-11-01)
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
_H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(_H, '..')); sys.path.insert(0, _H)
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
from rvtballet import server
import rvt_params, rvt_geometry as G
import rvt_untouched_report as U
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
DEFAULT = ['SWall', 'Floor', 'Ceiling', 'RoofBase', 'FootPrintRoof', 'ExtrusionRoof', 'FamilyInstance', 'RoomElem', 'RbsDuctCurve', 'RbsPipeCurve', 'RbsWireCurve', 'TextNote', 'LinearDimString', 'IndependentTag', 'Family', 'FamilySymbol',
           'DBViewPlan', 'DBViewSection', 'DBView3d', 'Viewport', 'DBDrawing', 'Level', 'Grid', 'RefPlane', 'MaterialElem', 'BaseRailing']
KNOWN = set(rvt_params.PNAMES.values())
FIELD = {'Level': 'DatumPlane.m_text', 'Grid': 'DatumPlane.m_text', 'RefPlane': 'DatumPlane.m_text', 'DBView': 'DBView.m_viewName', 'FamilySymbol': 'SymbolInfo.m_name'}
NOEDIT = {'Name', 'Family and Type', 'Type', 'Type Id', 'Family'}
async def post(c, mid, op):
    r = await c.post('/api/m/%s/edit' % mid, json=op); j = await r.json(); return r.status, j
async def one_class(c, models, k, src, cls, pr, ix):
    row = {'class': cls}; ids = [e for e, v in ix.items() if str(v) == cls and e in pr]; row['class_elements'] = len(ids)
    if not ids: row['result'] = 'ABSENT'; return row
    mid = 'c%d' % k; md = os.path.join(_T, 'm%d' % k); os.makedirs(md); work = os.path.join(_T, 'w%d.rvt' % k); shutil.copy(src, work); h0 = sha(work)
    models.m[mid] = {'dir': md, 'name': 'f', 'src': work}
    info = await (await c.get('/api/m/%s/saveinfo' % mid)).json()
    if not info.get('open'): row['result'] = 'NOT_OPEN ' + str(info.get('error'))[:80]; return row
    applied = []; refused = {}; used = set()
    for kind in ('set_string', 'set_num', 'move', 'set_field'):
        tried = 0; skip = set()
        for eid in ids:
            if (eid in used and not os.environ.get('C3X_SAME_ELEMENT')) or tried >= 40: continue
            p = g(pr[eid])
            if kind == 'set_string':
                cands = [n for n, v in p.items() if isinstance(v, str) and '|' not in n and n not in NOEDIT and n in KNOWN]
                if not cands: continue
                cands = [n for n in sorted(cands, key=lambda n: p[n] != '') if (eid, n) not in skip]
                if not cands: continue
                nm = cands[0]
                op = {'op': 'set_string', 'eid': eid, 'param': nm, 'value': 'c3x edit'}
            elif kind == 'set_num':
                cands = [n for n, v in p.items() if isinstance(v, float) and '|' not in n and n not in NOEDIT and n in KNOWN and (eid, n) not in skip]
                if not cands: continue
                nm = cands[0]
                op = {'op': 'set_num', 'eid': eid, 'param': nm, 'value': p[nm] + 0.5, 'kind': 'Double'}
            elif kind == 'set_field':
                f = FIELD.get(cls) or next((v for k3, v in FIELD.items() if cls.startswith(k3)), None); nm = next((p[k5] for k5 in ('Name', 'View Name', 'Type Name') if isinstance(p.get(k5), str) and p[k5]), None)
                if not f or not nm: continue
                op = {'op': 'set_string', 'eid': eid, 'field': f, 'value': nm + ' c3x', 'match': nm, 'param': None}
            else: op = {'op': 'move', 'eid': eid, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}
            tried += 1; st, j = await post(c, mid, op)
            if st == 200: applied.append(op); used.add(eid); break
            refused[kind] = (j.get('error') or j.get('code') or '')[:70]
            if kind == 'set_num' and op.get('param'): skip.add((eid, op['param'])); ids.insert(ids.index(eid) + 1, eid) if len(cands) > 1 and sum(1 for k4 in skip if k4[0] == eid) < 8 else None
            if kind == 'set_string' and op.get('param'): skip.add((eid, op['param'])); ids.insert(ids.index(eid) + 1, eid) if len(cands) > 1 and sum(1 for k4 in skip if k4[0] == eid) < 6 else None
    row['applied'] = [o['op'] + ('(field)' if o.get('field') and not o.get('param') else '') for o in applied]; row['refused'] = refused; row['applied_ops'] = [(o['op'], o['eid'], o.get('param') or o.get('field')) for o in applied]
    if not applied: row['result'] = 'NO_EDIT_ACCEPTED'; return row
    out = os.path.join(_T, 'o%d.rvt' % k); t0 = time.time(); r = await c.post('/api/m/%s/saveas' % mid, json={'dest': out}); j = await r.json(); row['saveas_s'] = round(time.time() - t0, 1)
    if r.status != 200: row['result'] = 'SAVEAS_REFUSED_%d %s' % (r.status, j.get('code')); row['detail'] = str(j.get('error'))[:200]; row['n_unexpected'] = (j.get('report') or {}).get('n_unexpected'); row['report_keys'] = sorted((j.get('report') or {}).keys()); row['report_raw'] = str(j.get('report'))[:1500]; row['unexpected_sample'] = str((j.get('report') or {}).get('unexpected') or j.get('unexpected'))[:400]; return row
    row['verify_diffs'] = j['verify']['n_unexpected']
    po = rvt_params.params(out); bad = []
    for o in applied:
        a, b = g(pr.get(o['eid'])), g(po.get(o['eid'])); ch = {x for x in set(a) | set(b) if a.get(x) != b.get(x)}
        if o['op'] != 'move' and o.get('param') and not (o['param'] in ch): bad.append('target_unchanged:%s' % o['op'])
        if o['op'] != 'move' and o.get('param') and [x for x in ch - {o['param']} - {q.get('param') for q in applied if q['eid'] == o['eid']} if b.get(x) != b.get(o['param'])]: bad.append('side_effect:%s:%d' % (o['op'], len(ch - {o['param']})))      # aliases of the same stored value (e.g. Number / Room Number|String) carry the new value and are not side effects
    others = [e for e in pr if e not in used and g(pr[e]) != g(po.get(e))]; row['other_elements_param_changed'] = len(others)
    if others:
        names = set()
        for e in others:
            a2, b2 = g(pr[e]), g(po.get(e)); names |= {x for x in set(a2) | set(b2) if a2.get(x) != b2.get(x)}
        row['others_changed_params'] = sorted(names)[:8]
        if names <= {'View Name', 'View Name|String', 'Sheet Name', 'Panel Schedule Name', 'Associated Level', 'Associated Level|String', 'Level', 'Host|String', 'Work Plane|String', 'Column Location Mark', 'Column Location Mark|String', 'IfcGUID', 'Type IfcGUID'} and row.get('verify_diffs') == 0: row['declared_dependents'] = len(others)   # gate-declared derived View Name (Viewer/Viewport); verify passed
        else: bad.append('others_changed')
    row.update({k2: v for k2, v in U.report(work, out).items() if not k2.startswith('_')})
    t0 = time.time(); r = await c.post('/api/m/%s/save' % mid, json={}); j2 = await r.json(); row['save_s'] = round(time.time() - t0, 1)
    if r.status == 409 and j2.get('code') == 'layout_changed': row['save_over'] = 'refused_layout_changed'; row['detail'] = str(j2.get('error'))[:120]      # deliberate: re-paged partition not confirmed in Revit; SAVE AS stays the path
    elif r.status != 200: bad.append('SAVE!_refused_%d_%s' % (r.status, j2.get('code'))); row['detail'] = str(j2.get('error'))[:200]
    else:
        if sha(work) != sha(out): bad.append('save!_bytes_differ_from_saveas')
        bk = j2.get('backup'); row['backup'] = bool(bk)
        if not bk: bad.append('no_backup')
        else:
            r = await c.post('/api/m/%s/restore' % mid, json={'confirm': True, 'n': 0}); jr = await r.json()
            if r.status != 200 or sha(work) != h0: bad.append('restore_not_original_%d' % r.status)
    kd = os.environ.get('KEEP_DIR')
    if kd: os.makedirs(kd, exist_ok=True); shutil.copy(out, os.path.join(kd, '%s_%s%s' % (os.environ.get('KEEP_TAG', 'f'), cls, os.path.splitext(src)[1])))
    os.remove(out); row['problems'] = bad; row['result'] = 'OK' if not bad and row['verify_diffs'] == 0 else 'PROBLEM'; return row
async def main(out, src, classes):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    pr = rvt_params.params(src); ix = G.file_geometry_index(src); rows = []
    if classes == ['ALL']: classes = DEFAULT
    models = server.Models()
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        for k, cl in enumerate(classes):
            rows.append(await one_class(c, models, k, src, cl, pr, ix)); print(rows[-1], flush=True)
            try: c.app['saves'].close('c%d' % k)      # release the loaded model of this class: held models made later classes fail 'too_big' (memory guard) in a 2024 HVAC run
            except Exception: pass
            models.m.pop('c%d' % k, None); import gc; gc.collect()
            try: os.remove(os.path.join(_T, 'w%d.rvt' % k))
            except OSError: pass
    json.dump(rows, open(out, 'w'), indent=1); print('CLASS-PASS', {'classes': len(rows), 'ok': sum(r['result'] == 'OK' for r in rows), 'absent': sum(r['result'] == 'ABSENT' for r in rows)})
def isolated(out, src, classes):
    """one fresh process per class: the in-process loop kept growing (10 GB after 3 classes on a 5 MB template, 25 GB on the 22 MB HVAC file); a child's memory is released when it exits. Rows are the children's output, merged into the same OUT.json."""
    import subprocess, tempfile as _tf
    rows = []
    for cl in (DEFAULT if classes == ['ALL'] else classes):
        o = _tf.mktemp(suffix='.json', prefix='cp1-')
        r = subprocess.run([sys.executable, os.path.abspath(__file__), o, src, cl], env=dict(os.environ, RVT_CP_CHILD='1'), stdout=subprocess.PIPE, text=True)
        sys.stdout.write(''.join(l for l in r.stdout.splitlines(True) if not l.startswith('CLASS-PASS'))); sys.stdout.flush()
        try: rows += json.load(open(o)); os.remove(o)
        except Exception: rows.append({'class': cl, 'result': 'CHILD_FAILED', 'rc': r.returncode})
    json.dump(rows, open(out, 'w'), indent=1); print('CLASS-PASS', {'classes': len(rows), 'ok': sum(r['result'] == 'OK' for r in rows), 'absent': sum(r['result'] == 'ABSENT' for r in rows)})
_cl = sys.argv[3].split(',')
if os.environ.get('RVT_CP_CHILD') or os.environ.get('RVT_CP_INPROC') or (len(_cl) == 1 and _cl != ['ALL']): asyncio.run(main(sys.argv[1], sys.argv[2], _cl))
else: isolated(sys.argv[1], sys.argv[2], _cl)
