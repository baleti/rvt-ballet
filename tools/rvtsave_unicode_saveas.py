"""SAVE AS of non-ASCII (BMP) and long string values (Mark param) on a REAL Autodesk 2024 .rvt (the synthetic cols2 .rte is NOT a valid .rvt for Revit, controls fail too). usage: rvtsave_unicode_saveas.py SRC.rvt OUTDIR  -> OUTDIR/uni_<tag>.rvt, prints status per case. Then rvt_vm_open.py 2024 OUTDIR/*.rvt"""
import os, sys, asyncio, tempfile, shutil, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server
CASES = {'ascii': 'Plain ASCII', 'latin': 'Ünïcödé ñ ß é', 'cjk': '日本語テスト 中文', 'cyr': 'Тест Привет', 'long': 'L' * 600, 'longuni': 'ü日' * 300, 'quote': 'a"b\'c<d>&e\\f'}
async def run(RTE, out):
    from rvtballet import save
    pr = save._read_params(open(RTE, 'rb').read())
    c0 = [(e, v['params']['Mark']) for e, v in sorted(pr.items()) if e >= 1000 and isinstance(v.get('params', {}).get('Mark'), str)]
    EID, OLD = c0[0]
    from aiohttp.test_utils import TestClient, TestServer
    os.makedirs(out, exist_ok=True)
    for tag, val in CASES.items():
        src = os.path.join(_T, tag + '.rvt'); shutil.copy(RTE, src); md = os.path.join(_T, 'm' + tag); os.makedirs(md)
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': EID, 'param': 'Mark', 'value': val, 'match': OLD}); e = r.status
            dest = os.path.join(out, 'uni_%s.rvt' % tag); r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json()
            print(tag, 'edit', e, 'saveas', r.status, j.get('code', 'ok'), os.path.exists(dest), flush=True)
asyncio.run(run(sys.argv[1], sys.argv[2]))
