"""SAVE AS destinations that are not plain new files (existing directory, FIFO, missing parent dir, empty string, NUL in path, symlink to a victim file, symlink to a directory) with overwrite+confirm: no crash, no 5xx, nothing outside the destination changed (victim file, directory contents, source), no temp debris"""
import atexit, shutil as _sh, tempfile as _tf
_made = []; _mk = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mk(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, json, hashlib, errno
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo'); r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'ro'}); assert r.status == 200, await r.text()
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 281147, 'param': 'Comments', 'value': 'sa'}); assert r.status == 200
        V = os.path.join(_T, 'victim.bin'); open(V, 'wb').write(b'precious'); hv = sha(V)
        DD = os.path.join(_T, 'adir'); os.mkdir(DD); open(DD + '/keep.txt', 'w').write('k')
        os.mkfifo(os.path.join(_T, 'ff.rvt')); os.symlink(V, os.path.join(_T, 'lnk_victim.rvt')); os.symlink(DD, os.path.join(_T, 'lnk_dir.rvt'))
        dests = {'dir': DD, 'fifo': os.path.join(_T, 'ff.rvt'), 'missing_parent': os.path.join(_T, 'nope', 'x', 'o.rvt'), 'empty': '', 'nul': os.path.join(_T, 'a\x00b.rvt'),
                 'lnk_victim': os.path.join(_T, 'lnk_victim.rvt'), 'lnk_dir': os.path.join(_T, 'lnk_dir.rvt')}
        bad = []
        for k, dst in dests.items():
            r = await c.post('/api/m/m/saveas', json={'dest': dst, 'overwrite': True, 'confirm': True}); st = r.status
            try: j = await r.json()
            except Exception: j = {'error': (await r.text())[:90]}
            print(k, st, str(j.get('code')), str(j.get('error'))[:90])
            if st >= 500 and st != 507: bad.append((k, st, 'server error'))      # 507 = clean 'cannot write' refusal (symlink to a directory)
            if sha(src) != h0: bad.append((k, 'source changed'))
            if sha(V) != hv: bad.append((k, 'victim file through symlink was overwritten (state: %d)' % st))
            if sorted(os.listdir(DD)) != ['keep.txt']: bad.append((k, 'directory contents changed', os.listdir(DD)))
        left = [f for f in os.listdir(_T) if f.endswith(('.part', '.sgtmp'))]
        print('bad:', bad, 'debris:', left)
        assert not bad and not left, (bad, left)
    print('odd SAVE AS destinations handled without damage')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
