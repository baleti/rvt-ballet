"""Two parameter edits (set_string Keynote + set_num Cost) on ONE element in one SAVE AS, either order: the read-back used to count the sibling edit as 'other parameter changed' and refuse (c6x-rvtmatrix item 8). Now saved; both values read back, nothing else on the element changed, source untouched.
Autodesk 2024 template only."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte'); E = 281147
A = {'op': 'set_string', 'eid': E, 'param': 'Keynote', 'value': 'c3x edit'}; B = {'op': 'set_num', 'eid': E, 'param': 'Cost', 'value': 1.5, 'kind': 'Double'}
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    h0 = sha(SRC); a = rvt_params.params(SRC)[E]; a = a.get('params', a)
    for name, ops in (('AB', [A, B]), ('BA', [B, A])):
        md = os.path.join(_T, 'm' + name); os.makedirs(md); m = server.Models(); m.m['m'] = {'dir': md, 'name': 'a', 'src': SRC}
        async with TestClient(TestServer(server.make_app(m))) as c:
            for o in ops: r = await c.post('/api/m/m/edit', json=o); assert r.status == 200, (name, r.status)
            out = os.path.join(_T, name + '.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); assert r.status == 200, (name, r.status, (await r.text())[:200])
        b = rvt_params.params(out)[E]; b = b.get('params', b)
        assert b['Keynote'] == 'c3x edit' and abs(b['Cost'] - 1.5) < 1e-9, (name, b['Keynote'], b['Cost'])
        extra = {k for k in set(a) | set(b) if a.get(k) != b.get(k)} - {'Keynote', 'Cost'}
        assert all(b.get(k) == b.get('Keynote') or b.get(k) == b.get('Cost') for k in extra), (name, extra)
    assert sha(SRC) == h0
asyncio.run(run()); print('save same element pair OK (Keynote + Cost, both orders)')
