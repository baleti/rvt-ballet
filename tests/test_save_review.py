"""regressions from the code review of the save path: overwrite=true needs confirm, hardlink to the source refused, restore refused while a save runs, layout check that cannot run FAILS CLOSED
(overwrite refused, SAVE AS warns), an edit recorded while a save runs is not deleted by the save's clearing."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, types
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
EDIT = {'op': 'set_string', 'field': 'ParamValueAString.m_value', 'value': 'rev', 'match': ''}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    app = server.make_app(models)
    async with TestClient(TestServer(app)) as c:
        saves = app['saves']; await c.get('/api/m/m/saveinfo')
        other = os.path.join(_T, 'other.rvt'); shutil.copy(RTE, other)
        r = await c.post('/api/m/m/saveas', json={'dest': other, 'overwrite': True}); assert r.status == 400 and sha(other) == h0, r.status       # no confirm
        hl = os.path.join(_T, 'hard.rvt'); os.link(src, hl)
        for ow in (False, True):
            r = await c.post('/api/m/m/saveas', json={'dest': hl, 'overwrite': ow, 'confirm': True}); j = await r.json(); assert r.status == 400 and j['code'] == 'bad_dest' and sha(src) == h0, (r.status, j)
        saves.busy.add('m'); r = await c.post('/api/m/m/restore', json={'confirm': True, 'n': 0}); assert r.status == 423; saves.busy.discard('m')
        assert (await c.post('/api/m/m/edit', json=dict(EDIT, eid=24))).status == 200
        # layout check cannot run -> fail closed
        orig = save.layout_changes; save.layout_changes = lambda a, b: None
        try:
            r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 409 and j['code'] == 'layout_changed' and sha(src) == h0, (r.status, j)
            d = os.path.join(_T, 'o.rvt'); j = await (await c.post('/api/m/m/saveas', json={'dest': d})).json(); assert j['ok'] and 'could not run' in j['warnings'][0], j
        finally: save.layout_changes = orig
    # an edit recorded while the save runs survives the clearing after a successful overwrite
    ss = save.SaveSessions(); ss.doc('m2', src); save.add_edit(ss, 'm2', src, dict(EDIT, eid=24))
    sg = save._import(); real = sg.save
    def fake(doc, nb, man, force=False): ss.edits('m2').ops.append(dict(EDIT, eid=25, value='late')); return types.SimpleNamespace(dest=doc.path, size=1, sha256='0' * 64, backup=None, version='2024', elapsed=0, report={})
    sg.save = fake; save.layout_changes = lambda a, b: []
    try: save.save_overwrite(ss, 'm2', src)
    finally: sg.save = real; save.layout_changes = orig
    assert [o['eid'] for o in ss.edits('m2').ops] == [25], ss.edits('m2').ops
    print('save review OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
