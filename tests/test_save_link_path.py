"""c3x-rvtlink (derived from test_save_link_host, c6x item 16): path string of the RvtLinkSymbol edited through the product path with same-length, longer and unicode values on the 2024 Snowdon HVAC sample (1363937).
 in-place SAVE! on a Revit 2024 project that HOLDS link instances (VM-made host with 2 RvtLinkInstance + RvtLinkSymbol): (a) set_string on ProjectInfo, (b) move of a link instance, (c) set_string on a link instance.
Each case must either be refused (edit time or save time, file byte-identical) or saved with verify_diffs 0, a backup equal to the original, and the link instance / link symbol records otherwise unchanged; RESTORE brings the original back byte-identical."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
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
    cases = [('sym_str_short', {'op': 'set_string', 'eid': 1363937, 'value': 'X', 'match': ''}), ('sym_str_long', {'op': 'set_string', 'eid': 1363937, 'value': 'L' * 300, 'match': ''}), ('sym_str_uni', {'op': 'set_string', 'eid': 1363937, 'value': 'caf\u00e9_\u4e2d\u6587_\U0001F600', 'match': ''})]
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for name, op in cases:
            r = await c.post('/api/m/m/edit', json=op); j = await r.json()
            if r.status != 200: print(name, 'refused at edit', r.status, j.get('code'), (j.get('error') or '')[:260]); assert sha(src) == h0; continue
            r = await c.post('/api/m/m/save', json={}); j = await r.json()
            if r.status != 200: print(name, 'refused at save', r.status, j.get('code')); assert sha(src) == h0, 'refused save changed the file'
            else:
                print(name, 'saved, unexpected diffs', j['verify']['n_unexpected']); assert j['verify']['n_unexpected'] == 0 and j['verify']['objects_src'] == j['verify']['objects_out'], j['verify']
                assert j.get('backup') and sha(j['backup']) == h0, 'backup is not the original'; assert sha(src) != h0
                if os.environ.get('KEEP_DIR'): shutil.copy(src, os.path.join(os.environ['KEEP_DIR'], name + '.rvt'))
                r = await c.post('/api/m/m/restore', json={'backup': j['backup'], 'confirm': True}); assert r.status == 200, await r.text(); assert sha(src) == h0, 'restore not byte-identical'
            await c.post('/api/m/m/edit/undo', json={})
    assert sha(src) == h0; assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
