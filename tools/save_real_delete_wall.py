"""DELETE of Wall elements on a REAL project through the server API (rvtedit backend, delete enabled), SAVE AS each. Safe outcomes: refused at edit, refused at save with no output file,
or saved with verify_diffs 0 and every dependent declared. Anything else (saved with undeclared change) is an ESCAPE. Aggregate output only.
usage: tools/save_real_delete_wall.py OUT.json FILE [N]"""
import os, sys, asyncio, tempfile, json, subprocess, sqlite3, shutil, atexit, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_DELETE_ANY'] = '1'; atexit.register(shutil.rmtree, _T, True)
os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import server
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def main(out, src, n):
    h0 = sha(src); row = {'cases': []}
    r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', src, _T + '/c_src'], capture_output=True, text=True, timeout=3600); assert r.returncode == 0
    walls = [x[0] for x in sqlite3.connect(_T + '/c_src/model.sqlite').execute("select id from el where cls in ('Wall','SWall') order by id limit ?", (n,))]; row['walls_tried'] = len(walls)
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    models = server.Models(); md = os.path.join(_T, 'm'); os.makedirs(md); models.m['m'] = {'dir': md, 'name': 'f', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for w in walls:
            r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': w}); j = await r.json()
            if r.status != 200: row['cases'].append('refused_edit:' + j.get('error', '')[:60]); continue
            dest = os.path.join(_T, 'o%d.rvt' % w); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json()
            if r.status != 200: row['cases'].append('refused_save:%s output_exists=%s' % (j.get('code'), os.path.exists(dest)))
            else: row['cases'].append('SAVED verify_diffs=%s objects %s->%s absent_expect=%s' % (j['verify']['n_unexpected'], j['verify'].get('objects_src'), j['verify'].get('objects_out'), sum(1 for x in j.get('expectations', []) if x.get('kind') == 'absent')) + ' manifest_keys=%s must_delete=%s' % (sorted(j.get('manifest', {}))[:8], len(j.get('manifest', {}).get('must_delete', []) or [])))
            await c.post('/api/m/m/edit/undo', json={})
    row['source_untouched'] = sha(src) == h0; print(row); json.dump(row, open(out, 'w'))
asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2))
