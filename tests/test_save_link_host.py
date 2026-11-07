"""c6x-rvtwrite item 16: in-place SAVE! on a Revit 2024 project that HOLDS link instances (VM-made host with 2 RvtLinkInstance + RvtLinkSymbol): (a) set_string on ProjectInfo, (b) move of a link instance, (c) set_string on a link instance.
Each case must either be refused (edit time or save time, file byte-identical) or saved with verify_diffs 0, a backup equal to the original, and the link instance / link symbol records otherwise unchanged; RESTORE brings the original back byte-identical."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/studyx-tests/links/w/mk_link24.rvt')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp, subprocess
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, _T + '/c0'], capture_output=True, text=True); assert r.returncode == 0, r.stderr[-300:]
    db = sqlite3.connect(_T + '/c0/model.sqlite')
    pi = db.execute("select id from el where cls='ProjectInfo'").fetchone()[0]; li = [x[0] for x in db.execute("select id from el where cls='RvtLinkInstance' order by id")]; assert len(li) == 2, li
    cases = [('projinfo_string', {'op': 'set_string', 'eid': pi, 'value': 'c6x test', 'match': ''}), ('link_move', {'op': 'move', 'eid': li[0], 'dx': 1.0}), ('link_delete', {'op': 'delete', 'eid': li[1]}), ('link_num_int', {'op': 'set_num', 'eid': li[0], 'param': 'Mark', 'value': 5, 'kind': 'Int'}), ('link_num_dbl', {'op': 'set_num', 'eid': li[0], 'param': 'Mark', 'value': 5.0}), ('link_string', {'op': 'set_string', 'eid': li[1], 'value': 'c6x test', 'match': ''})]
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for name, op in cases:
            r = await c.post('/api/m/m/edit', json=op); j = await r.json()
            if r.status != 200: print(name, 'refused at edit', r.status, j.get('code') or j.get('error', '')[:80]); assert sha(src) == h0; continue
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
