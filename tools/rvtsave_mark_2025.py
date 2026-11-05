"""RESEARCH ONLY: Mark string edit SAVE AS on a 2025 file with the 2025 gate bypass (production refuses 2025). usage: rvtsave_mark_2025.py SRC.rvt OUT.rvt"""
import os, sys, asyncio, tempfile, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2025': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
async def run(src, out):
    from rvtballet import save, server
    save._import(); from savegate import adapters; adapters.RVT_WRITABLE = tuple(adapters.RVT_WRITABLE) + ('2025',)
    from aiohttp.test_utils import TestClient, TestServer
    pr = save._read_params(open(src, 'rb').read())
    c0 = [(e, v['params']['Mark']) for e, v in sorted(pr.items()) if e >= 1000 and isinstance(v.get('params', {}).get('Mark'), str)]
    print('Mark candidates', len(c0))
    if not c0: return
    e, old = c0[0]; md = tempfile.mkdtemp(dir=_T); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': e, 'param': 'Mark', 'value': 'MK25', 'match': old}); print('edit', r.status, (await r.text())[:200])
        r = await c.post('/api/m/m/saveas', json={'dest': out}); print('saveas', r.status, (await r.text())[:300], os.path.exists(out))
asyncio.run(run(*sys.argv[1:3]))
