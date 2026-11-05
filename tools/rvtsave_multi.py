"""Several edits on DIFFERENT elements in one gated SAVE AS: Mark on A, Mark on B, move C, (optional delete D). Usage: rvtsave_multi.py src.rvt out.rvt. Autodesk samples only for public use."""
import sys, os, asyncio, tempfile, json
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
async def run(src, out):
    from rvtballet import server, save as S
    from savegate import rvt_elements as R
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    b = open(src, 'rb').read(); pr = S._read_params(b); d = R.elements(b)
    fi = [e for e, v in d.items() if v.startswith('FamilyInstance|') and e > 1000 and json.loads(v.split('|')[1])[2]]
    mk = [e for e in fi if pr.get(e, {}).get('params', {}).get('Mark') is not None]
    A, B = mk[0], mk[1]; C = next(e for e in fi if e not in (A, B))
    md = tempfile.mkdtemp(); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        c.session._timeout = aiohttp.ClientTimeout(total=None); await c.get('/api/m/m/saveinfo')
        for body in ({'op': 'set_string', 'eid': A, 'param': 'Mark', 'value': 'MA1'}, {'op': 'set_string', 'eid': B, 'param': 'Mark', 'value': 'MB2'}, {'op': 'move', 'eid': C, 'dx': 1.5}) + (({'op': 'delete', 'eid': next(e for e, v in d.items() if v.startswith(os.environ.get('MULTI_DELETE', 'FamilyInstance') + '|') and e > 1000)},) if os.environ.get('MULTI_DELETE') else ()):
            r = await c.post('/api/m/m/edit', json=body); print(body['op'], body['eid'], r.status, (await r.text())[:120] if r.status != 200 else '')
            if r.status != 200: return
        if os.environ.get('MULTI_INPLACE'): r = await c.post('/api/m/m/save', json={}); print('SAVE! in place', r.status, str((await r.json()).get('error'))[:200]); return
        r = await c.post('/api/m/m/saveas', json={'dest': out}); print('saveas', r.status, str((await r.json()).get('error'))[:200])
if os.environ.get('MULTI_INPLACE'): os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
asyncio.run(run(sys.argv[1], sys.argv[2]))
