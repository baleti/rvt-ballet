import sys, os, asyncio, tempfile, json, hashlib
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research'), '.']
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
async def run(src):
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    md = tempfile.mkdtemp(); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        for u, b in (('saveinfo', None), ('edit', {'op': 'move', 'eid': 1365188, 'dx': 1.0}), ('save', {})):
            r = await (c.get('/api/m/m/' + u) if b is None else c.post('/api/m/m/' + u, json=b)); print(' ', u, r.status, (await r.text())[:110].replace('\n', ' '))
asyncio.run(run(sys.argv[1]))
