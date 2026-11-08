"""c7x-rvtread 119: change_type and set_type_num through the real server + savegate gate (HVAC 2024 sample, new rules: frozen streams, ElemTable/Latest ids, gzip CRC): both SAVE AS must be accepted (200, output same size). Run: python3 tests/test_save_fullpath_typeops.py (slow, ~10 min)"""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_CHANGETYPE='1', RVTBALLET_ENABLE_TYPEPARAM='1')
sys.path.insert(0, os.path.expanduser('~/src/rvt-viewer'))
dd = os.path.expanduser('~/rvt-research/corpus/2024'); RTE = os.path.join(dd, [n for n in os.listdir(dd) if n.endswith('HVAC.rvt')][0])
from rvtballet import server, save
import aiohttp
T = aiohttp.ClientTimeout(total=3000)
async def run(op):
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); md = os.path.join(_T, 'm' + op['op']); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        r = await c.post('/api/m/m/edit', json=op, timeout=T); j = await r.json(); print(op['op'], 'edit', r.status, str(j)[:100])
        out = os.path.join(_T, 'o_%s.rvt' % op['op']); r = await c.post('/api/m/m/saveas', json={'dest': out}, timeout=T); j = await r.json()
        print(op['op'], 'saveas', r.status, str(j.get('error') or j.get('code') or 'ok')[:150], os.path.exists(out) and os.path.getsize(out) == os.path.getsize(RTE))
assert os.path.exists(RTE)
for op in ({'op': 'change_type', 'eid': 1379181, 'type_eid': 1530089}, {'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 0.1}):
    asyncio.run(run(op))
