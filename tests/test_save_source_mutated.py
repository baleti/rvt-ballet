"""c4x-rvtmatrix: SAVE! when the source file is truncated / zeroed / grown / bit-flipped (a) AFTER load (race) and (b) BEFORE load. Never a silent overwrite: after-load mutation must be refused (not 200) with the mutated file left byte-identical and no temp files;
before-load mutation must be refused with the file unchanged, or (if the file still parses) saved with a backup equal to the mutated source. Autodesk 2024 template only."""
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip: no template'); sys.exit(0)
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
from rvtballet import server
import rvt_params
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def mutate(p, how):
    b = bytearray(open(p, 'rb').read())
    if how == 'zero': b = bytearray()
    elif how == 'half': b = b[:len(b) // 2]
    elif how == 'minus1': b = b[:-1]
    elif how == 'grow': b += b'\0' * 1000
    elif how == 'flip_hdr': b[0] ^= 0xFF
    elif how == 'flip_mid': b[len(b) // 2] ^= 0xFF
    open(p, 'wb').write(b)
HOWS = ['zero', 'half', 'minus1', 'grow', 'flip_hdr', 'flip_mid']
EID = next(e for e, d in rvt_params.params(SRC).items() if g(d).get('Comments') == '')
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    import aiohttp
    res = {}
    for phase in ('after', 'before'):
        for how in HOWS:
            src = os.path.join(_T, 's.rte'); shutil.copy(SRC, src); md = os.path.join(_T, 'm_%s_%s' % (phase, how)); os.makedirs(md)
            if phase == 'before': mutate(src, how)
            models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
            async with TestClient(TestServer(server.make_app(models)), timeout=aiohttp.ClientTimeout(total=None)) as c:
                info = await (await c.get('/api/m/m/saveinfo')).json()
                if phase == 'before' and not info.get('open'): res[(phase, how)] = 'not_open'; assert sha(src) == hashlib.sha256(open(src, 'rb').read()).hexdigest(); continue
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': EID, 'param': 'Comments', 'value': 'mutated-source test'})
                if r.status != 200: res[(phase, how)] = 'edit_%d' % r.status; continue
                if phase == 'after': mutate(src, how)
                h = sha(src); r = await c.post('/api/m/m/save', json={}); j = await r.json()
                if phase == 'after': assert r.status != 200, (phase, how, r.status, j.get('code'))
                if r.status != 200: assert sha(src) == h, ('source changed by a refused save', phase, how)
                else: assert j.get('backup') and sha(j['backup']) == h, ('saved without a backup equal to the mutated source', phase, how)
                res[(phase, how)] = '%d %s' % (r.status, j.get('code'))
            assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))], 'temp left'
    return res
res = asyncio.run(run()); shutil.rmtree(_T, True); print('OK source_mutated', res)
