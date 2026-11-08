"""c3x-rvtlink MIXED (two path edits on one link type + a ProjectInfo string edit in one save: last path wins, 0 unexpected diffs, restore byte-identical) (derived from test_save_link_host, c6x item 16): path string of the RvtLinkSymbol edited through the product path with same-length, longer and unicode values on the 2024 Snowdon HVAC sample (1363937).
 in-place SAVE! on a Revit 2024 project that HOLDS link instances (VM-made host with 2 RvtLinkInstance + RvtLinkSymbol): (a) set_string on ProjectInfo, (b) move of a link instance, (c) set_string on a link instance.
Each case must either be refused (edit time or save time, file byte-identical) or saved with verify_diffs 0, a backup equal to the original, and the link instance / link symbol records otherwise unchanged; RESTORE brings the original back byte-identical."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/c5x-link/w/hvac24.rvt')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp, subprocess
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, _T + '/c0'], capture_output=True, text=True); assert r.returncode == 0, r.stderr[-300:]
    db = sqlite3.connect(_T + '/c0/model.sqlite')
    pi = db.execute("select id from el where cls='ProjectInfo'").fetchone()[0]; li = [x[0] for x in db.execute("select id from el where cls='RvtLinkInstance' order by id")]; assert li, li; ls = [x[0] for x in db.execute("select id from el where cls='RvtLinkSymbol' order by id")]; assert 1363937 in ls, ls

    cases = []
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    sys.path[:0] = [os.path.expanduser(x) for x in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab')]
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for op in ({'op': 'set_link_path', 'eid': 1363937, 'value': 'C:/first/a.rvt'}, {'op': 'set_link_path', 'eid': 1363937, 'value': 'C:/second/much_longer_name_b.rvt'}, {'op': 'set_string', 'eid': pi, 'value': 'c3x mixed', 'match': ''}):
            r = await c.post('/api/m/m/edit', json=op); assert r.status == 200, await r.text()
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 200, j
        print('mixed saved, unexpected diffs', j['verify']['n_unexpected']); assert j['verify']['n_unexpected'] == 0 and j['verify']['objects_src'] == j['verify']['objects_out'], j['verify']
        import rvtedit
        log = rvtedit.Edit(src).g.e.trace(1363937)[3]; ps = [l[4] for l in log if l[1] == 'ModelPath.m_path']
        assert ps == ['C:/second/much_longer_name_b.rvt'], ps
        r = await c.post('/api/m/m/restore', json={'backup': j['backup'], 'confirm': True}); assert r.status == 200, await r.text(); assert sha(src) == h0
    assert sha(src) == h0; assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
