"""c2x-rvtwrite item 11 (CAD link ImportInstance move; derived from c6x item 16): in-place SAVE! on a Revit 2024 project that HOLDS link instances (VM-made host with 2 RvtLinkInstance + RvtLinkSymbol): (a) set_string on ProjectInfo, (b) move of a link instance, (c) set_string on a link instance.
Each case must either be refused (edit time or save time, file byte-identical) or saved with verify_diffs 0, a backup equal to the original, and the link instance / link symbol records otherwise unchanged; RESTORE brings the original back byte-identical."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, sqlite3
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser(os.environ.get('CAD_SRC') or '~/rvtfix/corpus/2023/36_rst_basic_sample_project.rvt'); EID = int(os.environ.get('CAD_EID') or 1382352)      # CAD_SRC/CAD_EID: a Revit-made 2024 host (tools/rvt_diff_vm.py linkdwg) and its ImportInstance id
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp, subprocess
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src); md = os.path.join(_T, 'm'); os.makedirs(md)
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, _T + '/c0'], capture_output=True, text=True); assert r.returncode == 0, r.stderr[-300:]; db = sqlite3.connect(_T + '/c0/model.sqlite'); assert db.execute("select cls from el where id=%d" % EID).fetchone()[0] == 'ImportInstance'
    cases = [('cad_move', {'op': 'move', 'eid': EID, 'dx': 1.0}), ('cad_string', {'op': 'set_string', 'eid': EID, 'value': 'c2x test', 'match': ''}), ('cad_move_dy', {'op': 'move', 'eid': EID, 'dy': -2.5}), ('cad_move_dz', {'op': 'move', 'eid': EID, 'dz': 0.5}), ('cad_rotate', {'op': 'rotate', 'eid': EID, 'deg': 30})]
    if os.environ.get('CAD_ONLY'): cases = [c for c in cases if c[0] in os.environ['CAD_ONLY'].split(',')]      # e.g. CAD_ONLY=cad_move_dz: one case per run (each save costs minutes on a loaded host)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for name, op in cases:
            r = await c.post('/api/m/m/edit', json=op); j = await r.json()
            if r.status != 200: print(name, 'refused at edit', r.status, json.dumps(j)[:400]); assert sha(src) == h0; continue
            r = await c.post('/api/m/m/save', json={}); j = await r.json()
            if r.status != 200: print(name, 'refused at save', r.status, j.get('code')); assert sha(src) == h0, 'refused save changed the file'
            else:
                assert name != 'cad_rotate', 'rotate of a CAD link has no Revit-verified implementation and must be refused'
                print(name, 'saved, unexpected diffs', j['verify']['n_unexpected']); assert j['verify']['n_unexpected'] == 0 and j['verify']['objects_src'] == j['verify']['objects_out'], j['verify']
                assert j.get('backup') and sha(j['backup']) == h0, 'backup is not the original'; assert sha(src) != h0
                if os.environ.get('KEEP_DIR'): shutil.copy(src, os.path.join(os.environ['KEEP_DIR'], name + '.rvt'))
                r = await c.post('/api/m/m/restore', json={'backup': j['backup'], 'confirm': True}); assert r.status == 200, await r.text(); assert sha(src) == h0, 'restore not byte-identical'
            await c.post('/api/m/m/edit/undo', json={})
    assert sha(src) == h0; assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]
    print('OK')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
