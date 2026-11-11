"""c6x-rvtmatrix: hostile calls on edit/undo, edits/recover, edits, edits/stored, unknown/odd model ids (never 5xx, source unchanged); sibling of the /edit test: (non-JSON, JSON list/null/number, value as list/dict/number, 5 MB string, 2000-deep nesting, huge eid, NUL): every answer is 4xx JSON (never 500, never 200), nothing is recorded, the source file is byte-identical. Synthetic 2024 cols2 scene."""
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
CASES = [('POST', '/api/m/m/edit/undo', b''), ('POST', '/api/m/m/edit/undo', b'{{{'), ('POST', '/api/m/m/edit/undo', b'{"n":-5}'), ('POST', '/api/m/m/edit/undo', b'[1]'),
         ('POST', '/api/m/m/edits/recover', b''), ('POST', '/api/m/m/edits/recover', b'null'), ('POST', '/api/m/m/edits/recover', b'{{{'),
         ('GET', '/api/m/m/edits', b''), ('GET', '/api/m/m/edits/stored', b''), ('GET', '/api/m/m/backups', b''),
         ('POST', '/api/m/nope/edit/undo', b''), ('POST', '/api/m/nope/edits/recover', b''), ('GET', '/api/m/nope/edits', b''),
         ('POST', '/api/m/..%2f..%2fetc/edit/undo', b''), ('POST', '/api/m/%00/edit/undo', b''), ('GET', '/api/m/' + 'a' * 5000 + '/edits', b'')]
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = _T + '/s.rvt'; shutil.copy(RTE, src); h0 = sha(src); md = _T + '/m'; os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    bad = 0
    async with TestClient(TestServer(server.make_app(models))) as c:
        for k in range(2):      # twice: second pass runs after the undo-on-empty calls
            for meth, url, data in CASES:
                try:
                    r = await c.request(meth, url, data=data or None, headers={'Content-Type': 'application/json'}); st = r.status; txt = (await r.text())[:60]
                except Exception as e: st, txt = -1, type(e).__name__
                ok = st < 500 and st != -1
                if not ok: bad += 1
                print('%s %-8s %s %s' % (meth, url[:40], st, 'ok' if ok else 'BAD ' + txt))
        r = await c.get('/api/m/m/edits'); j = await r.json()
    assert j['ops'] == [], j
    assert sha(src) == h0, 'source changed'
    if bad: print('FAIL', bad); sys.exit(1)
    print('OK')
try: asyncio.run(run())
finally: shutil.rmtree(_T, ignore_errors=True)
