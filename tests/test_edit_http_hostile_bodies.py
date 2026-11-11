"""c6x-rvtmatrix: hostile bodies on POST /api/m/<id>/edit (non-JSON, JSON list/null/number, value as list/dict/number, 5 MB string, 2000-deep nesting, huge eid, NUL): every answer is 4xx JSON (never 500, never 200), nothing is recorded, the source file is byte-identical. Synthetic 2024 cols2 scene."""
import os, sys, asyncio, tempfile, shutil, json, hashlib
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_SNAPSHOT_CACHE=_T + '/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1')
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
E = 301595
RAW = {'not_json': b'{{{', 'empty': b'', 'list': b'[1,2]', 'null': b'null', 'number': b'5', 'string': b'"x"', 'deep': b'[' * 2000 + b']' * 2000,
       'big_string': json.dumps({'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 'a' * 5000000}).encode()}
OBJ = {'value_list': {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': ['a']}, 'value_dict': {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': {'a': 1}},
       'value_num': {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 5}, 'value_null': {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': None},
       'eid_huge': {'op': 'set_string', 'eid': 10 ** 30, 'param': 'Comments', 'value': 'x'}, 'eid_str': {'op': 'set_string', 'eid': '301595', 'param': 'Comments', 'value': 'x'},
       'eid_neg': {'op': 'move', 'eid': -1, 'dx': 1}, 'nul': {'op': 'set_string', 'eid': E, 'param': 'Comments', 'value': 'a\x00b'}, 'op_list': {'op': ['move'], 'eid': E}, 'op_none': {'eid': E},
       'param_dict': {'op': 'set_string', 'eid': E, 'param': {'x': 1}, 'value': 'x'}, 'dx_str': {'op': 'move', 'eid': E, 'dx': '1'}, 'dx_nan': {'op': 'move', 'eid': E, 'dx': float('nan')}}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/s.rvt'; shutil.copy(RTE, src); h0 = sha(src); md = _T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    bad = 0
    async with TestClient(TestServer(server.make_app(models))) as c:
        cases = [(k, v) for k, v in RAW.items()] + [(k, json.dumps(v).encode()) for k, v in OBJ.items()]
        for name, data in cases:
            try:
                r = await c.post('/api/m/m/edit', data=data, headers={'Content-Type': 'application/json'}); st = r.status; txt = (await r.text())[:60]
            except Exception as e: st, txt = -1, type(e).__name__
            ok = 400 <= st < 500
            if not ok: bad += 1
            print('%-12s %s %s' % (name, st, 'ok' if ok else 'BAD ' + txt))
        r = await c.get('/api/m/m/edits'); j = await r.json()
    assert j['ops'] == [], j
    assert sha(src) == h0, 'source changed'
    if bad: print('FAIL', bad); sys.exit(1)
    print('OK')
try: asyncio.run(run())
finally: shutil.rmtree(_T, ignore_errors=True)
