"""edit -> saveas: a string-parameter edit on one element is declared in the manifest, savegate verify (element level) passes, only that element's value
differs in the output (re-read), source untouched; undo drops the op from the next save; unsupported ops / fields refused."""
import os, sys, asyncio, tempfile, hashlib, shutil, time
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WL = os.path.expanduser('~/rvt-research/write-lab'); RTE = WL + '/scenes/classtests/2024_writer_cols2.rte'
from rvtballet import server, save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
LEVEL = 355                                        # 'Level 1': renaming it changes 31 dependent elements (derived Level parameter)
MAT = 24                                           # MaterialElem with empty string parameters: isolated edit target
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'a.rvt'); shutil.copy(RTE, src); h0 = sha(src)
    md = os.path.join(_T, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        bad = [{'op': 'delete', 'eid': 1}, {'op': 'set_string', 'eid': 'x', 'value': 'a'}, {'op': 'set_string', 'eid': MAT, 'value': 'a', 'field': 'Element.m_id'},
               {'op': 'set_string', 'eid': LEVEL, 'value': 'a\0b', 'field': 'DatumPlane.m_text'}, {'op': 'set_string', 'eid': LEVEL, 'value': 'x' * 5000, 'field': 'DatumPlane.m_text'}]
        for b in bad:
            r = await c.post('/api/m/m/edit', json=b); assert r.status == 400 and (await r.json())['code'] == 'edit_error', (b, r.status)
        r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 999999999, 'value': 'a', 'field': 'DatumPlane.m_text'}); assert r.status == 400, await r.text()
        # a level rename alters 31 dependents; since 6512f7f they are declared DERIVED ECHOES (strict rule: only the edited parameter, old->new value): 200, n_unexpected 0, 31 warned, source untouched
        j = await (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': LEVEL, 'value': 'Level 1 Renamed Longer', 'field': 'DatumPlane.m_text'})).json(); assert j['ok']
        dx = os.path.join(_T, 'x.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': dx}); j = await r.json()
        assert r.status == 200 and j['verify']['n_unexpected'] == 0 and any(w.startswith(tuple(str(n) + ' other' for n in range(31, 60))) for w in j['warnings']) and os.path.exists(dx) and sha(dx) != h0 and sha(src) == h0, (r.status, j.get('error'), j.get('warnings'))
        assert (await (await c.post('/api/m/m/edit/undo')).json())['n'] == 0
        j = await (await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': MAT, 'value': 'Edited by test', 'match': ''})).json()
        assert j['ok'] and j['manifest'] == {'modified': ['el:%d' % MAT]}, j
        d1 = os.path.join(_T, 'e1.rvt'); t0 = time.time(); r = await c.post('/api/m/m/saveas', json={'dest': d1}); j = await r.json(); dt = time.time() - t0
        assert r.status == 200 and j['ok'] and sha(d1) != h0 and sha(src) == h0, (r.status, j)
        assert j['verify']['n_unexpected'] == 0, j
        # re-read: the level name changed, nothing else (the library verify already compared every element; here the name is checked directly)
        sys.path.insert(0, WL); import wlrec
        m = wlrec.Model(d1); pn, i, rr, log, q = list(m.find(MAT))[0]
        assert any(l[1] == 'ParamValueAString.m_value' and l[4] == 'Edited by test' for l in log), 'new value not found in output'
        # undo -> next save is an identity copy
        j = await (await c.post('/api/m/m/edit/undo')).json(); assert j['ok'] and j['n'] == 0, j
        assert (await c.post('/api/m/m/edit/undo')).status == 400
        d2 = os.path.join(_T, 'e2.rvt'); j = await (await c.post('/api/m/m/saveas', json={'dest': d2})).json(); assert sha(d2) == h0, 'undo did not drop the op'
        print('save edit OK (edited saveas %.1fs, size %d -> %d)' % (dt, os.path.getsize(src), os.path.getsize(d1)))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
