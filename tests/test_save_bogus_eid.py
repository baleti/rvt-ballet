"""Edit ops with element ids that cannot exist (negative, zero, 2**31, 2**63, 2**200) on an Autodesk 2024 template: each is either refused at /edit or,
if queued, SAVE AS refuses; never a 500/raw exception, nothing written, source untouched."""
import os, sys, asyncio, tempfile, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    md = os.path.join(_T, 'm'); os.makedirs(md); h0 = sha(SRC); bad = []
    for eid in (-1, 0, 2**31, 2**63, 2**200):
        for op in ({'op': 'move', 'eid': eid, 'dx': 1.0}, {'op': 'rotate', 'eid': eid, 'deg': 10}):
            models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': SRC}
            async with TestClient(TestServer(server.make_app(models))) as c:
                r = await c.post('/api/m/m/edit', json=op); st = r.status
                if st < 400:
                    out = os.path.join(_T, 'o%d.rvt' % len(bad)); r2 = await c.post('/api/m/m/saveas', json={'dest': out}); st2 = r2.status
                    if st2 >= 500 or (st2 == 200 and sha(out) != h0 and False): bad.append((eid.bit_length(), op['op'], st, st2))
                    if st2 == 200: bad.append(('SAVED-NONEXISTENT', eid.bit_length(), op['op']))
                elif st >= 500: bad.append((eid.bit_length(), op["op"], st, await r.text()))
    assert not bad, bad
    assert sha(SRC) == h0
asyncio.run(run()); print('OK bogus eids refused or not saved')
