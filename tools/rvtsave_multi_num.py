"""Double + Int + Bool(0/1 Int) parameter edits on THREE different elements in ONE gated SAVE AS (item 68). Usage: rvtsave_multi_num.py src.rvt out.rvt. Autodesk samples only for public use. Prints the ops, then re-reads out.rvt and reports changed params."""
import sys, os, asyncio, tempfile, json
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {y: 'open' for y in os.environ.get('GATE_YEARS', '2024,2026').split(',')}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
BOOLNAMES = set(os.environ.get('BOOLNAMES', 'Return Airflow,Power Load Units,Lighting Load Units').split(','))      # NOTE: these three are now refused by edit.REVIT_IGNORES_STORED_INT (Revit VM readback shows no effect)
BOOLNAMES0 = None      # 0/1 params that really have a stored ParamValueInt (item 69: the other 0/1 reader values are derived defaults)
NOEDIT = {'Phase', 'Phase Filter', 'Type', 'Family'}
async def run(src, out):
    import hashlib, shutil
    from rvtballet import save
    if '2025' in os.environ.get('GATE_YEARS', ''):      # RESEARCH ONLY, in-process: production still refuses 2025
        save._import(); from savegate import adapters; adapters.RVT_WRITABLE = tuple(adapters.RVT_WRITABLE) + ('2025',)
    inplace = bool(os.environ.get('INPLACE'))
    if inplace: os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; orig = src; src = out; shutil.copy(orig, src); h0 = hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12]      # INPLACE=1: out is a private copy that SAVE! overwrites
    from rvtballet import server, save as S
    import rvt_params
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    pr = S._read_params(open(src, 'rb').read()); known = set(rvt_params.PNAMES.values())
    cands = {'Double': [], 'Bool': [], 'Int': []}
    for e in sorted(pr):
        if e < 1000: continue
        for n, v in pr[e].get('params', {}).items():
            if '|' in n or n in NOEDIT or n not in known or n.startswith('Family'): continue
            if isinstance(v, float): cands['Double'].append((e, n, v, {'op': 'set_num', 'eid': e, 'param': n, 'value': v + 0.5, 'kind': 'Double'}))
            elif isinstance(v, int) and v in (0, 1) and n in BOOLNAMES: cands['Bool'].append((e, n, v, {'op': 'set_num', 'eid': e, 'param': n, 'value': 1 - v, 'kind': 'Int'}))
            elif isinstance(v, int) and 2 <= v <= 1000: cands['Int'].append((e, n, v, {'op': 'set_num', 'eid': e, 'param': n, 'value': v + 1, 'kind': 'Int'}))
    print({k: len(v) for k, v in cands.items()}); ops = []; used = set()
    md = tempfile.mkdtemp(); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
        for k in ('Double', 'Bool', 'Int'):
            tried = 0
            for e, n, v, body in cands[k]:
                if e in used: continue
                tried += 1; r = await c.post('/api/m/m/edit', json=body)
                if r.status == 200: ops.append(body); used.add(e); print(k, e, n, v, '->', body['value'], 200); break
                if tried >= 60: break
            else: print(k, 'no candidate accepted', tried)
            if tried >= 60 and not any(o in ops for o in [x[3] for x in cands[k]]): print(k, 'gave up after 60 refusals', (await r.text())[:120])
        if not ops: return
        if inplace:
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); print('SAVE! in place', r.status, str(j.get('error'))[:200]); h1 = hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12]; print('sha', h0, '->', h1)
            if r.status != 200: return
            bk = await (await c.get('/api/m/m/backups')).json(); print('backups', [(b['n'], b['size']) for b in bk])
            import shutil as _s; _s.copy(src, src + '.edited')
            rr = await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); print('restore', rr.status, 'sha', hashlib.sha256(open(src, 'rb').read()).hexdigest()[:12], 'want', h0)
            _s.move(src + '.edited', src); return
        r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json(); print('saveas', r.status, str(j.get('error'))[:200], 'verify_diffs', (j.get('verify') or {}).get('n_unexpected'))
        if r.status != 200: return
    po = rvt_params.params(out)
    for o in ops:
        g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
        print('readback', o['eid'], o['param'], g(pr[o['eid']]).get(o['param']), '->', g(po[o['eid']]).get(o['param']), 'want', o['value'])
    print('other elements changed', sum(1 for e in pr if e not in used and pr[e] != po.get(e)))
asyncio.run(run(sys.argv[1], sys.argv[2]))
