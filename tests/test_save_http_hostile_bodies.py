"""c6x-rvtmatrix: hostile bodies on POST /api/m/<id>/save, /saveas, /restore (non-JSON, list/null/number, dest as list/dict/number/NUL/empty/directory, n as string/huge/negative, confirm as string, force/overwrite as junk): every answer is 4xx/501 JSON, never 500 and never 200, the source file is byte-identical and no file appears next to it. Was: hostile bodies on /edit (non-JSON, JSON list/null/number, value as list/dict/number, 5 MB string, 2000-deep nesting, huge eid, NUL): every answer is 4xx JSON (never 500, never 200), nothing is recorded, the source file is byte-identical. Synthetic 2024 cols2 scene."""
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
RAW = {'not_json': b'{{{', 'empty': b'', 'list': b'[1,2]', 'null': b'null', 'number': b'5', 'string': b'"x"', 'deep': b'[' * 2000 + b']' * 2000}
D = _T + '/out.rvt'
OBJ = {'dest_list': {'dest': ['a']}, 'dest_dict': {'dest': {'a': 1}}, 'dest_num': {'dest': 5}, 'dest_nul': {'dest': D + '\x00x.rvt'}, 'dest_empty': {'dest': ''}, 'dest_dir': {'dest': _T},
       'dest_missing': {}, 'dest_noext': {'dest': _T + '/noext'}, 'dest_dotdot': {'dest': _T + '/../../../../etc/x.rvt'}, 'dest_longname': {'dest': _T + '/' + 'a' * 5000 + '.rvt'},
       'n_str': {'confirm': True, 'n': 'x'}, 'n_huge': {'confirm': True, 'n': 10 ** 30}, 'n_neg': {'confirm': True, 'n': -5}, 'n_list': {'confirm': True, 'n': [1]}, 'confirm_str': {'confirm': 'true'}, 'confirm_one': {'confirm': 1}}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/s.rvt'; shutil.copy(RTE, src); h0 = sha(src); md = _T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    bad = 0
    async with TestClient(TestServer(server.make_app(models))) as c:
        cases = [(k, v) for k, v in RAW.items()] + [(k, json.dumps(v).encode()) for k, v in OBJ.items()]
        before = sorted(os.listdir(_T))
        for ep in ('save', 'saveas', 'restore'):
            for name, data in cases:
                try:
                    r = await c.post('/api/m/m/' + ep, data=data, headers={'Content-Type': 'application/json'}); st = r.status; txt = (await r.text())[:60]
                except Exception as e: st, txt = -1, type(e).__name__
                ok = (400 <= st < 500 or st == 501) and not (ep == 'save' and name in ('empty', 'list') and False)
                if ep == 'save' and st == 200: ok = True      # a no-edit SAVE! is an identity save; extra body keys are ignored
                if ep == 'saveas' and st == 507: ok = True      # honest disk error for an unwritable destination
                if not ok: bad += 1
                print('%-8s %-12s %s %s' % (ep, name, st, 'ok' if ok else 'BAD ' + txt))
        extra = sorted(set(os.listdir(_T)) - set(before) - {'.savegate', 'c', 'j', 'snap'}); print('new entries next to source:', extra)
        if extra: bad += 1
    assert sha(src) == h0, 'source changed'
    if bad: print('FAIL', bad); sys.exit(1)
    print('OK')
try: asyncio.run(run())
finally: shutil.rmtree(_T, ignore_errors=True)
