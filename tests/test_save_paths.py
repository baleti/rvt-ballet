"""SAVE AS destination edge cases through the API: non-ASCII + spaces, very long path, read-only folder, other filesystem (/dev/shm), missing folder,
directory as destination, same path as the source. Failures must write nothing and leave no .sgtmp / lock; source sha never changes."""
import os, sys, asyncio, tempfile, hashlib, shutil, stat
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def leftovers(d): return [f for f in os.listdir(d) if 'sgtmp' in f or f.endswith('.lock') or f.endswith('.part')]

async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src)
    md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    res = {}
    async with TestClient(TestServer(server.make_app(models))) as c:
        async def go(name, dest, ok, **kw):
            r = await c.post('/api/m/m/saveas', json=dict(dest=dest, **kw)); j = await r.json(); res[name] = r.status
            assert sha(src) == h0, name + ': source changed'
            if ok: assert r.status == 200 and sha(dest) == h0, (name, r.status, j)
            else: assert r.status >= 400 and r.status != 500 or r.status == 507, (name, r.status, j); assert not os.path.exists(dest) or os.path.isdir(dest) or dest == src, name
            return j
        d = os.path.join(_T, 'ünï cödé 日本語 dir'); os.makedirs(d); await go('unicode', os.path.join(d, 'ñame with spaces ü.rvt'), True); assert not leftovers(d)
        deep = _T
        while len(deep) < 300: deep = os.path.join(deep, 'segment_%02d_abcdefghijklmnopqrstuvwxyz' % (len(deep) // 40))
        os.makedirs(deep); await go('longpath>300', os.path.join(deep, 'x.rvt'), True); assert not leftovers(deep)
        ro = os.path.join(_T, 'ro'); os.makedirs(ro); os.chmod(ro, stat.S_IRUSR | stat.S_IXUSR)
        try:
            if os.geteuid() != 0: await go('readonly', os.path.join(ro, 'x.rvt'), False); assert os.listdir(ro) == []
            else: res['readonly'] = 'skipped (root)'
        finally: os.chmod(ro, 0o700)
        if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK):
            sd = tempfile.mkdtemp(dir='/dev/shm')
            try: await go('other-fs(/dev/shm)', os.path.join(sd, 'x.rvt'), True); assert not leftovers(sd)
            finally: shutil.rmtree(sd, ignore_errors=True)
        await go('missing-folder', os.path.join(_T, 'nope', 'x.rvt'), False)
        dd = os.path.join(_T, 'adir'); os.makedirs(dd); await go('dest-is-dir', dd, False)
        j = await go('same-as-source', src, False)
        j = await go('same-as-source+overwrite', src, False, overwrite=True); assert j['code'] == 'bad_dest', j
        assert not leftovers(_T) and not os.path.exists(src + '.lock')
    print('save paths OK', res)

if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
