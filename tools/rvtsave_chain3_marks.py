"""CHAIN: 3 in-place SAVE! on a private copy (out), each after one Mark edit on a different element; prints sha per step, then compares the final file with the base through the reader (only the 3 edited elements may differ). Usage: rvtsave_chain3_marks.py src.rvt out.rvt (Autodesk samples only for public use)."""
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ.update(RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', SAVEGATE_GATE=_T + '/gate.json', RVTBALLET_SNAPSHOT_CACHE='0')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params, aiohttp
from aiohttp.test_utils import TestClient, TestServer
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
sh = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
async def main(src, out):
    base = rvt_params.params(src); eids = [e for e, d in base.items() if isinstance(g(d).get('Mark'), str)][:3]
    shas = []; shutil.copy(src, out); md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': out}; print('sha0', sh(out))
    async with TestClient(TestServer(server.make_app(models))) as cl:
        cl.session._timeout = aiohttp.ClientTimeout(total=None); await cl.get('/api/m/m/saveinfo')
        for i, e in enumerate(eids):
            r = await cl.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': 'Mark', 'value': 'c%d' % i}); assert r.status == 200, await r.text()
            r = await cl.post('/api/m/m/save', json={'confirm': True}); t = await r.text(); print('save', i + 1, r.status, t[:100], 'sha', sh(out), flush=True); assert r.status == 200; shas.append(sh(out))
        if os.environ.get('RESTORE_N'):      # restore an OLDER backup (n=1: state after save 1 when 3 saves were made)
            bk = await (await cl.get('/api/m/m/backups')).json(); print('backups', [(b['n'], b['size']) for b in bk])
            r = await cl.post('/api/m/m/restore', json={'n': int(os.environ['RESTORE_N']), 'confirm': True}); print('restore', r.status, 'sha', sh(out), 'states', [sh(src)] + shas)
    if os.environ.get('RESTORE_N'): print('restored file Marks', [g(rvt_params.params(out)[e]).get('Mark') for e in eids]); return
    po = rvt_params.params(out)
    print('eids', eids)
    print('readback', [g(po[e]).get('Mark') for e in eids], 'other elements changed', sum(1 for e in base if e not in eids and base[e] != po.get(e)))
asyncio.run(main(sys.argv[1], sys.argv[2]))
