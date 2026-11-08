"""set_num edge values (nan, inf, extremes, -0.0, denormal): each must be refused (nothing written) or read back EXACTLY with only that parameter changed."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, sqlite3, subprocess, hashlib, math
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
FLOOR = 301567; P = 'Height Offset From Level'
VALS = [float('nan'), float('inf'), float('-inf'), 1e308, -1e308, 5e-324, -0.0, 0.0, 1e-9, 123456789.123456789, -1.0, 1e15]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def table(d): return {(r[0], r[1]): r[2] for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select e.id, p.k, p.v from prm p join el e on e.i=p.i')}
def conv(f, n):
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', f, os.path.join(_T, n)], capture_output=True, text=True, timeout=600); assert r.returncode == 0, r.stderr[-200:]; return table(os.path.join(_T, n))
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}; base = conv(src, 'c0'); res = {}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for k, v in enumerate(VALS):
            r = await c.post('/api/m/m/edit', json={'op': 'set_num', 'eid': FLOOR, 'param': P, 'value': v})
            if r.status != 200: res[repr(v)] = 'refused_input'; continue
            out = os.path.join(_T, 'o%d.rvt' % k); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
            if r.status != 200: res[repr(v)] = 'refused_gate'; assert not os.path.exists(out); await c.post('/api/m/m/edit/undo'); continue
            b = conv(out, 'c%d' % (k + 1)); d = {x for x in base.keys() | b.keys() if base.get(x) != b.get(x)}
            ok = d <= {(FLOOR, P)} and (not d or math.isclose(float(b[(FLOOR, P)]), v, rel_tol=1e-12, abs_tol=1e-300))
            res[repr(v)] = ('OK ' + str(b.get((FLOOR, P)))) if ok else 'DAMAGE %s %s' % (sorted(d)[:3], b.get((FLOOR, P)))
            await c.post('/api/m/m/edit/undo')
    assert sha(src) == h0; print(res)
    bad = {k: v for k, v in res.items() if v.startswith('DAMAGE')}; assert not bad, bad
    print('save numedge OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
