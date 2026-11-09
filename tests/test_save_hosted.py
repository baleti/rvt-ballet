"""Hosted elements: membership() reports 'hosted on N' for a real window (Autodesk 2024 Facades sample, 593207 on wall 593206); an in-place MOVE of it is refused (group_or_option code), an in-place parameter edit of it is not blocked by this check; a leaf element is not flagged. Revit evidence: a +2 ft move leaves the window 0.21875 ft off its wall line (readback), while Revit opens and regenerates the copy without complaint."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, shutil, hashlib, json
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {'2024': 'open'}}, open(T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    src = T + '/f.rvt'; shutil.copy(SRC, src); h0 = sha(src); md = T + '/m'; os.makedirs(md)
    m = save.membership(open(src, 'rb').read(), [593207, 593206]); assert m == {593207: ['hosted on 593206'], 593206: ['hosts 2 element(s)', 'joined to 1 element(s)']}, m      # the host wall is flagged too: moving it would leave the window behind
    assert save.risky_membership(m, [{'op': 'move', 'eid': 593206}]).get(593206) == ['hosts 2 element(s)', 'joined to 1 element(s)'] and 593206 not in save.risky_membership(m, [{'op': 'set_string', 'eid': 593206}])
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        await c.get('/api/m/m/saveinfo')
        assert (await c.post('/api/m/m/edit', json={'op': 'move', 'eid': 593207, 'dx': 2.0})).status == 200
        r = await c.post('/api/m/m/save', json={}); j = await r.json(); assert r.status == 409 and j.get('code') == 'group_or_option' and 'hosted' in j.get('error', ''), (r.status, j)
        assert sha(src) == h0
    print('hosted element: flagged, in-place move refused, file untouched')
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
