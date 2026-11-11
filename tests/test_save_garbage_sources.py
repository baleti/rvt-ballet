"""0-byte, tiny garbage, text and DWG-header files named .rvt: edit+in-place save must never return 200 and the file stays byte-identical."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'      # the test is about the pending-edit bookkeeping, not the layout rule
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]

CASES = {'zero': b'', 'garbage512': bytes(range(256)) * 2, 'text': b'this is not a revit file\n' * 50, 'dwg_header': b'AC1032' + b'\0' * 4000,
         'cfb_magic_only': bytes.fromhex('D0CF11E0A1B11AE1') + b'\0' * 4000}
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    bad = 0
    for name, data in CASES.items():
        src = os.path.join(_T, name + '.rvt'); open(src, 'wb').write(data)
        md = os.path.join(_T, 'm_' + name); os.makedirs(md)
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        st = {}
        try:
            async with TestClient(TestServer(server.make_app(models))) as c:
                r = await c.get('/api/m/m/saveinfo'); st['info'] = r.status
                r = await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 301595, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}); st['edit'] = r.status
                r = await c.post('/api/m/m/save', json={}); st['save'] = r.status
        except Exception as e: st['exc'] = type(e).__name__
        same = open(src, 'rb').read() == data
        print(name, st, 'untouched' if same else 'CHANGED')
        if st.get('save') == 200 or not same: bad += 1
    if bad: print('FAIL', bad); sys.exit(1)
    print('all refused, sources byte-identical')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
