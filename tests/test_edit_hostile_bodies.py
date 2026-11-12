"""HTTP level: hostile /edit bodies (20 MB value, 100k-deep nesting, 200k keys, not JSON, 200k-op list) are refused with 4xx, memory stays bounded, the model file is byte-identical and a following valid edit still works."""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        import time, resource
        bodies = {'big_value_20MB': json.dumps({'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'x' * (20 << 20)}),
                  'nested_100k': '[' * 100000 + ']' * 100000,
                  'many_keys_1M': json.dumps({'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'a', **{'k%d' % i: 1 for i in range(200000)}}),
                  'not_json': 'x' * 1000, 'ops_list_200k': json.dumps([{'op': 'move', 'eid': 281147, 'dx': 1.0}] * 200000)}
        for name, body in bodies.items():
            t0 = time.time(); r = await c.post('/api/m/m/edit', data=body, headers={'Content-Type': 'application/json'}); txt = (await r.text())[:100].replace('\n', ' ')
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
            print(name, r.status, round(time.time() - t0, 1), 's', 'maxrss MB', rss, txt, flush=True)
            assert r.status in (400, 413, 422), (name, r.status, txt)
            assert sha(src) == h0
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ok'}); assert r.status == 200, await r.text()
    print('oversized / hostile edit bodies refused (4xx), model untouched, later valid edit still works')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
