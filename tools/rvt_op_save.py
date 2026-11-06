"""RVT-EDIT (c5x-rvtmatrix): apply ONE op (JSON) to a private copy, SAVE AS through the gate, then SAVE! in place; reader check of which elements changed. Keeps OUT.rvt if KEEP_OUT is set. change_type is enabled here.
usage: tools/rvt_op_save.py FILE.rvt '{"op":"set_num","eid":585072,"param":"Unconnected Height","value":21.0}'   (Autodesk samples only; aggregate lines, no names)"""
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
async def main(src, op):
    inst = op['eid']
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    work = os.path.join(_T, 'w.rvt'); shutil.copy(src, work); h0 = sha(work); pr = rvt_params.params(work)
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': work}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        assert (await (await c.get('/api/m/m/saveinfo')).json()).get('open')
        r = await c.post('/api/m/m/edit', json=op); j = await r.json(); print('edit', r.status, str(j.get('error') or '')[:160])
        if r.status != 200: return
        out = os.path.join(_T, 'o.rvt'); t0 = time.time(); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json(); print('saveas', r.status, round(time.time() - t0, 1), 's', j.get('code'), str(j.get('error') or '')[:300])
        if r.status != 200: print('report', json.dumps(j.get('report') or {})[:600]); return
        print('verify_diffs', j['verify']['n_unexpected'], 'expectations', json.dumps(j.get('expectations'))[:300])
        po = rvt_params.params(out); diff = [e for e in pr if g(pr[e]) != g(po.get(e))]
        ch = sorted(k for k in set(g(pr[inst])) | set(g(po.get(inst))) if g(pr[inst]).get(k) != g(po.get(inst)).get(k)); print('target params changed:', [(k, g(pr[inst]).get(k), g(po[inst]).get(k)) for k in ch][:6]); print('elements whose reader params differ:', len(diff), 'only target:', diff == [inst])
        if os.environ.get('KEEP_OUT'): shutil.copy(out, os.environ['KEEP_OUT']); print('kept', os.environ['KEEP_OUT'])
        t0 = time.time(); r = await c.post('/api/m/m/save', json={}); j2 = await r.json(); print('save! in place', r.status, round(time.time() - t0, 1), 's', j2.get('code'), str(j2.get('error') or '')[:200], 'bytes==saveas', sha(work) == sha(out))
asyncio.run(main(sys.argv[1], json.loads(sys.argv[2])))
