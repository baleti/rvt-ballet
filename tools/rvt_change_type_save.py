"""RVT-EDIT rung 4 (c5x-rvtmatrix): change_type of one FamilyInstance to a same-family FamilySymbol, SAVE AS through the gate, then SAVE! in place on a private copy; reader check that ONLY the instance's type changed. Keeps OUT.rvt if KEEP_OUT is set.
usage: tools/rvt_change_type_save.py FILE.rvt INSTANCE_EID TYPE_EID   (Autodesk samples only; prints aggregate lines, no names)"""
import os, sys, asyncio, tempfile, time, json, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_CHANGETYPE='1', RVTBALLET_ALLOW_OVERWRITE='1')
import atexit; atexit.register(shutil.rmtree, _T, True); os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')
_H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(_H, '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
from rvtballet import server
import rvt_params
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src, inst, typ):
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    work = os.path.join(_T, 'w.rvt'); shutil.copy(src, work); h0 = sha(work); pr = rvt_params.params(work)
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        assert (await (await c.get('/api/m/m/saveinfo')).json()).get('open')
        r = await c.post('/api/m/m/edit', json={'op': 'change_type', 'eid': inst, 'type_eid': typ}); j = await r.json(); print('edit', r.status, str(j.get('error') or '')[:160])
        if r.status != 200: return
        out = os.path.join(_T, 'o.rvt'); t0 = time.time(); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json(); print('saveas', r.status, round(time.time() - t0, 1), 's', j.get('code'), str(j.get('error') or '')[:300])
        if r.status != 200: print('report', json.dumps(j.get('report') or {})[:600]); return
        print('verify_diffs', j['verify']['n_unexpected'], 'expectations', json.dumps(j.get('expectations'))[:300])
        po = rvt_params.params(out); diff = [e for e in pr if g(pr[e]) != g(po.get(e))]
        print('type id before/after', g(pr[inst]).get('Type Id'), g(po[inst]).get('Type Id'), '| elements whose reader params differ:', len(diff), 'only target:', diff == [inst])
        if os.environ.get('KEEP_OUT'): shutil.copy(out, os.environ['KEEP_OUT']); print('kept', os.environ['KEEP_OUT'])
        t0 = time.time(); r = await c.post('/api/m/m/save', json={}); j2 = await r.json(); print('save! in place', r.status, round(time.time() - t0, 1), 's', j2.get('code'), str(j2.get('error') or '')[:200], 'bytes==saveas', sha(work) == sha(out))
asyncio.run(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3])))
