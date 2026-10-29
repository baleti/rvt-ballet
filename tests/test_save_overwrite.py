"""POST /api/m/{mid}/save: 2x2 (allow_overwrite x gate) matrix, conflict -> 409, force needs confirm, backup restores the original."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
_T = __import__('tempfile').mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ.setdefault('SAVEGATE_CACHE', _T + '/c')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

async def case(tmp, allow, gate):
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(tmp, 'a%d%d.rvt' % (allow, gate)); shutil.copy(RTE, src)
    gf = os.path.join(tmp, 'gate.json'); json.dump({'rvt': {'2024': 'open'}} if gate else {}, open(gf, 'w'))
    os.environ['SAVEGATE_GATE'] = gf; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1' if allow else '0'
    os.environ['SAVEGATE_CACHE'] = os.path.join(tmp, 'bk')
    md = os.path.join(tmp, 'm%d%d' % (allow, gate)); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    h0 = sha(src); out = {}
    async with TestClient(TestServer(server.make_app(models))) as c:
        i = await (await c.get('/api/m/m/saveinfo')).json()
        assert i['open'] and i['allow_overwrite'] == bool(allow) and i['gate_open'] == bool(gate), i
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); out['plain'] = (r.status, j.get('code'))
        if allow and gate:
            assert r.status == 200 and j['backup'] and sha(src) == h0, j       # identity overwrite keeps bytes
            # conflict: change the file behind the viewer's back
            open(src, 'ab').write(b'\0' * 512)
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 409 and j['code'] == 'conflict', (r.status, j)
            r = await c.post('/api/m/m/save', json={'force': True}); assert r.status == 400          # force without confirm
            r = await c.post('/api/m/m/save', json={'force': True, 'confirm': True}); j = await r.json(); assert r.status == 200, j
            assert sha(src) == h0                                                                  # overwritten with the loaded bytes
        else:
            assert r.status == 409 and sha(src) == h0, (r.status, j)
    return out

async def run():
    tmp = tempfile.mkdtemp(); res = {}
    for allow in (0, 1):
        for gate in (0, 1): res[(allow, gate)] = await case(tmp, allow, gate)
    assert res[(0, 0)]['plain'][1] == 'overwrite_disabled' and res[(0, 1)]['plain'][1] == 'overwrite_disabled'
    assert res[(1, 0)]['plain'][1] == 'gate_closed' and res[(1, 1)]['plain'][0] == 200, res
    print('save overwrite OK', res)

if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip: savegate or scene missing')
else: asyncio.run(run())
