"""c2x-rvtmatrix items 9+10: on a private copy, edit 3 string params of FamilyInstances with NON-ASCII text (CJK, emoji, accents, 200 chars), SAVE! in place; then a second edit (ASCII, other element) and a SECOND SAVE! in place on the result.
Checks per save: 200, params re-read from the file on disk equal the request (round trip of the unicode text), no other element's params changed, backup chain restores save-1 state (n=0) and the original (n=1) by sha256.
Aggregate output only. KEEP_OUT=dir keeps the final file for a Revit VM open. usage: tools/rvt_double_save.py OUT.json FILE"""
import os, sys, asyncio, tempfile, json, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
import atexit; atexit.register(shutil.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); [sys.path.insert(0, os.path.expanduser(p)) for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/src/savegate')]
import rvt_params, rvt_geometry as G
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: ({k: repr(v) if isinstance(v, float) and v != v else v for k, v in (x.get('params', x) if isinstance(x, dict) else {}).items()})      # NaN != NaN would count unchanged elements as changed
TXT = ['中文测试 テスト 한글', 'café über Ñoño ß Łódź', 'emoji \U0001F600\U0001F680 end', 'x' * 200]
if os.environ.get('TXTMODE') == 'ascii': TXT = ['a1', 'b2', 'c3', 'd4']
async def main(out, src0):
    work = os.path.join(_T, 'w.rvt'); shutil.copy(src0, work); h0 = sha(work); json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
    row = {}; pr = rvt_params.params(work)
    from rvtballet import reader
    ix = G.file_geometry_index(work)
    fis = [e for e, v in ix.items() if str(v) == 'FamilyInstance' and e in pr]
    KN = set(rvt_params.PNAMES.values())
    def cand(e): return sorted(n for n, v in g(pr[e]).items() if isinstance(v, str) and '|' not in n and n in KN and n not in {'Name', 'Family and Type', 'Type', 'Type Id', 'Family'})
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        info = await (await c.get('/api/m/m/saveinfo')).json()
        if not info.get('open'): row['result'] = 'NOT_OPEN'; print(row); json.dump(row, open(out, 'w')); return
        applied = []; used = set()
        for e in fis:
            if len(applied) >= 3: break
            for nm in cand(e):
                v = TXT[len(applied)]
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': nm, 'value': v})
                if r.status == 200: applied.append((e, nm, v)); used.add(e); break
        row['unicode_edits'] = len(applied)
        if not applied: row['result'] = 'NO_EDIT'; print(row); json.dump(row, open(out, 'w')); return
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); row['save1'] = r.status; h1 = sha(work) if r.status == 200 else None
        if r.status != 200:
            row['detail'] = str(j.get('error'))[:160]; row['result'] = 'SAVE1_REFUSED_' + str(j.get('code'))
            o = os.path.join(_T, 'o.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': o}); j = await r.json(); row['saveas'] = r.status      # fallback path: SAVE AS (element verify) keeps the unicode round trip testable
            if r.status == 200:
                p1 = rvt_params.params(o); row['saveas_roundtrip_ok'] = sum(g(p1.get(e)).get(nm) == v for e, nm, v in applied); row['verify_diffs'] = j['verify']['n_unexpected']
                row['saveas_others_changed'] = sum(1 for e in pr if e not in used and g(pr[e]) != g(p1.get(e)))
                kd = os.environ.get('KEEP_OUT')
                if kd: os.makedirs(kd, exist_ok=True); shutil.copy(o, os.path.join(kd, 'uni_saveas.rvt'))
            else: row['detail_saveas'] = str(j.get('error'))[:160]
            print(row); json.dump(row, open(out, 'w')); return
        kd1 = os.environ.get('KEEP_OUT')
        if kd1: os.makedirs(kd1, exist_ok=True); shutil.copy(work, os.path.join(kd1, 'save1.rvt'))
        p1 = rvt_params.params(work); row['roundtrip_ok'] = sum(g(p1.get(e)).get(nm) == v for e, nm, v in applied); row['unicode_edits_total'] = len(applied)
        row['others_changed_1'] = sum(1 for e in pr if e not in used and g(pr[e]) != g(p1.get(e)))
        second = None
        for e in fis:
            if e in used: continue
            for nm in cand(e):
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': nm, 'value': 'second save'})
                if r.status == 200: second = (e, nm); break
            if second: break
        row['second_edit'] = bool(second)
        if second:
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); row['save2'] = r.status
            if r.status == 200:
                p2 = rvt_params.params(work); row['second_ok'] = g(p2.get(second[0])).get(second[1]) == 'second save'
                row['first_kept'] = sum(g(p2.get(e)).get(nm) == v for e, nm, v in applied)
                row['others_changed_2'] = sum(1 for e in pr if e not in used and e != second[0] and g(pr[e]) != g(p2.get(e)))
                kd = os.environ.get('KEEP_OUT')
                if kd: os.makedirs(kd, exist_ok=True); shutil.copy(work, os.path.join(kd, 'dbl_final.rvt'))
            else: row['detail2'] = str(j.get('error'))[:200]
        r = await c.post('/api/m/m/restore', json={'n': 0, 'confirm': True}); row['restore0'] = r.status; row['restore0_is_save1'] = h1 is not None and sha(work) == (h1 if row.get('save2') == 200 else h0)      # one backup per successful save: if save 2 was refused, n=0 is the original
        r = await c.post('/api/m/m/restore', json={'n': 1, 'confirm': True}); row['restore1'] = r.status; row['restore1_is_orig'] = sha(work) == h0
    row['result'] = 'OK' if row.get('roundtrip_ok') == len(applied) and row.get('second_ok') and row.get('first_kept') == len(applied) and not row.get('others_changed_1') and not row.get('others_changed_2') and row['restore0_is_save1'] and row['restore1_is_orig'] else 'PROBLEM'
    print(row); json.dump(row, open(out, 'w'))
asyncio.run(main(sys.argv[1], sys.argv[2]))
