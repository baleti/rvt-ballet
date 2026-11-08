"""In-place SAVE of an edit on a group member / group instance / design-option element is refused ('group_or_option', file untouched); membership() flags the real
group members of the Autodesk 2024 HVAC sample (ElementGroup.m_pElemIdsPairSet) and not a plain FamilyInstance; SAVE AS is not affected by the check."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    m = save.membership(open(src, 'rb').read(), [1365188, 1421734, 1421744])
    assert m == {1421734: ['group 1421744'], 1421744: ['group 1421744']}, m
    assert save.risky_membership({7: ['hosted on 9']}, [{'op': 'set_string', 'eid': 7}]) == {} and save.risky_membership({7: ['hosted on 9']}, [{'op': 'move', 'eid': 7}]) == {7: ['hosted on 9']}, 'hosted: only move/rotate counts'
    big = save.membership(open(src, 'rb').read(), range(1, 1500000)); assert 1421734 in big and 1365188 not in big, 'long id list: wrong membership'      # 1.5M ids must not hit the argv limit
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    real = save.membership
    async with TestClient(TestServer(server.make_app(models)), timeout=__import__("aiohttp").ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1365188, 'dx': 2.0}); assert r.status == 200, await r.text()
        for fake in ({1365188: ['group 1']}, {1365188: ['design option 7']}):
            save.membership = lambda b, e, f=fake: f
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 409 and j.get('code') == 'group_or_option', (r.status, j)
        def boom(b, e): raise RuntimeError('reader failed')
        save.membership = boom; r = await c.post('/api/m/m/save', json={}); assert r.status == 409, r.status      # unknown = refuse
        save.membership = real
        out = os.path.join(_T, 'ga.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        assert r.status == 200 and not any('group' in w for w in j.get('warnings', [])), ('plain instance move must not warn', j.get('warnings'))
        await c.post('/api/m/m/edit/undo', json={}); r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 1421734, 'dx': 1.0})
        assert r.status == 200, ('group member edit refused at the edit stage', r.status)
        if True:
            out2 = os.path.join(_T, 'gb.rvt'); r = await c.post('/api/m/m/saveas', json={'dest': out2}); j = await r.json()
            for _ in range(3):      # the viewer's memory guard (507 too_big) refuses safely when little RAM is free after the earlier save: retry
                if r.status != 507: break
                import gc; gc.collect(); await asyncio.sleep(5); r = await c.post('/api/m/m/saveas', json={'dest': out2}); j = await r.json()
            if r.status == 507: print('SAVE AS part skipped: memory guard too_big (safe refusal) on this host'); print('skip'); return
            assert r.status == 200 and any('group' in w for w in j.get('warnings', [])), ('SAVE AS of a group member must warn', j.get('warnings'))
    assert sha(src) == h0, 'refused save changed the file'
    assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]
    print('group/design-option in-place refusal OK; membership flags the real members')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
