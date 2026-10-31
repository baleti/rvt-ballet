"""several ops on the SAME element in one save are applied in the recorded order (QUEUE 83): move +2, rotate 30, move -2 (net: rotated in place), set Comments twice (last wins); the result equals the
same ops saved one after another (SAVE AS of the previous output as the next source): same converted bounding box, same parameters; verify clean, manifest declares the element once."""
import os, sys, asyncio, tempfile, shutil, subprocess, sqlite3, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
T = 301595; C = 281147      # T: the instance moved/rotated; C: an element with an empty stored Comments
OPS = [{'op': 'move', 'eid': T, 'dx': 2.0}, {'op': 'rotate', 'eid': T, 'deg': 30}, {'op': 'move', 'eid': T, 'dx': -2.0}]
def conv(f, name):
    d = os.path.join(_T, name); r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', f, d], capture_output=True, text=True, timeout=300); assert r.returncode == 0, r.stderr[-200:]
    c = sqlite3.connect(os.path.join(d, 'model.sqlite')); return {r[0]: json.loads(r[1]) for r in c.execute('select id, bb from el where bb is not null')}, {(r[0], r[1]): r[2] for r in c.execute('select e.id, p.k, p.v from prm p join el e on e.i=p.i')}
async def save_once(src, ops, dest, name):
    from aiohttp.test_utils import TestClient, TestServer
    md = os.path.join(_T, 'm_' + name); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        for op in ops:
            r = await c.post('/api/m/m/edit', json=op); j = await r.json(); assert r.status == 200, (op, j)
        assert set(j['manifest']['modified']) <= {'el:%d' % T, 'el:%d' % C} and len(j['manifest']['modified']) == len({'el:%d' % o['eid'] for o in ops}), j['manifest']
        r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json(); assert r.status == 200 and j['verify']['n_unexpected'] == 0, (r.status, j.get('error'))
async def run():
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); cm = [{'op': 'set_string', 'eid': C, 'param': 'Comments', 'value': 'first'}, {'op': 'set_string', 'eid': C, 'param': 'Comments', 'value': 'second'}]
    allops = OPS + cm
    one = os.path.join(_T, 'one.rvt'); await save_once(src, allops, one, 'one')
    cur = src
    for k, op in enumerate(allops):
        nxt = os.path.join(_T, 'step%d.rvt' % k); await save_once(cur, [op], nxt, 'step%d' % k); cur = nxt
    b1, p1 = conv(one, 'c_one'); b2, p2 = conv(cur, 'c_seq'); b0, p0 = conv(src, 'c_src')
    assert b1 == b2, 'bounding boxes differ between one save and sequential saves'
    assert p1 == p2, {k: (p1.get(k), p2.get(k)) for k in set(p1) | set(p2) if p1.get(k) != p2.get(k)}
    assert p1.get((C, 'Comments')) == 'second', p1.get((C, 'Comments'))
    moved = {i for i in b0 if i in b1 and b0[i] != b1[i]}; assert moved == {T}, moved
    pd = {k for k in set(p0) | set(p1) if p0.get(k) != p1.get(k)}; assert pd == {(C, 'Comments')}, pd      # no other parameter row of any element changed
    print('save same element OK: move/rotate/move + two Comments edits in one save == the same ops saved one by one (bounding boxes and parameters equal); only element %d moved (bounding box) and only (%d, Comments) differs in the parameter table; last Comments wins' % (T, C))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
