"""Malformed edit ops (set_string/set_num/delete/move/rotate with wrong types, huge/NUL/surrogate values, odd pids, unknown ops, repeated undo) posted to /edit on an
Autodesk 2024 template: every response is < 500 (clean refusal or ok), SAVE AS of any queued state is never a 5xx, source untouched."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
N = float('nan'); I = float('inf')
OPS = [{'op': o, 'eid': e} for o in ('set_string', 'set_num', 'delete', 'move', 'rotate', 'add', 'copy') for e in (None, 'x', 1.5, True, [], {})]
for v in (None, 1, [], 'a\0b', 'x' * 5000, '\ud83d', 'e\U0001f600', N, I, -I, 1e300, True, 2 ** 40, {}):
    for k in ('Double', 'Int', 'Bogus', None):
        OPS.append({'op': 'set_num', 'eid': 5, 'value': v, 'kind': k, 'param': 'Width'})
    OPS.append({'op': 'set_string', 'eid': 5, 'value': v, 'param': 'Comments'}); OPS.append({'op': 'set_string', 'eid': 5, 'value': v, 'pid': v})
    OPS.append({'op': 'move', 'eid': 5, 'dx': v, 'dy': v, 'dz': v}); OPS.append({'op': 'rotate', 'eid': 5, 'deg': v})
for pid in (-1, 0, 2 ** 31, 2 ** 70, 'x', 1.5, [], True): OPS.append({'op': 'set_num', 'eid': 5, 'value': 1, 'pid': pid}); OPS.append({'op': 'set_string', 'eid': 5, 'value': 'a', 'pid': pid})
OPS += [None, [], 'str', 5, {}, {'op': {}}, {'op': ['move']}]
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    md = os.path.join(_T, 'm'); os.makedirs(md); h0 = sha(SRC); bad = []
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': SRC}
    async with TestClient(TestServer(server.make_app(models))) as c:
        for i, op in enumerate(OPS):
            try: r = await c.post('/api/m/m/edit', data=json.dumps(op).encode() if True else None, headers={'Content-Type': 'application/json'})
            except Exception as e: bad.append((i, 'client', repr(e)[:60])); continue
            if r.status >= 500: bad.append((i, r.status, (await r.text())[:100], str(op)[:60]))
        for _ in range(3):
            r = await c.post('/api/m/m/edit/undo', json={})
            if r.status >= 500: bad.append(('undo', r.status))
        r = await c.post('/api/m/m/saveas', json={'dest': os.path.join(_T, 'o.rvt')})
        if r.status >= 500: bad.append(('saveas', r.status, (await r.text())[:100]))
    assert not bad, (len(bad), bad[:8])
    assert sha(SRC) == h0
asyncio.run(run()); print('OK %d malformed ops, no 5xx' % len(OPS))
