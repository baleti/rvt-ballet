"""LIMITED-verification SAVE AS of a by-name Comments edit on a REAL project too large for the element-level verify (rvtedit backend). Reports aggregate numbers only: seconds, changed gzip members, streams,
whether the output differs from the source only in the edited partition. usage: tools/save_real_light.py FILE"""
import os, sys, asyncio, tempfile, time, json, resource
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
async def main(src):
    row = {'size_mb': round(os.path.getsize(src) / 2 ** 20, 1)}; t0 = time.time()
    pr = rvt_params.params(src); cand = [e for e, d in pr.items() if g(d).get('Comments') == ''][:1]; row['params_seconds'] = round(time.time() - t0, 1); row['peak_rss_after_params_mb'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >> 10
    if not cand: row['result'] = 'NO_CANDIDATE'; print(row); return
    eid = cand[0]; del pr
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'limited-verify edit'}); row['edit_status'] = r.status
        if r.status != 200: row['result'] = 'EDIT_REFUSED'; row['detail'] = (await r.json()).get('error', '')[:100]; print(row); return
        t1 = time.time(); r = await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'o.rvt'), 'light_verify': True, 'confirm': True}); j = await r.json()
        row.update(save_status=r.status, code=j.get('code', 'ok'), save_seconds=round(time.time() - t1, 1), peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >> 10)
        if r.status == 200: row.update(changed_members=j['verify']['changed_members'], changed_streams=j['verify']['changed_streams'], limited=j.get('limited_verification'), result='OK')
        else: row['result'] = 'SAVE_%d' % r.status; row['detail'] = str(j.get('error'))[:160]
    print(row)
asyncio.run(main(sys.argv[1]))
