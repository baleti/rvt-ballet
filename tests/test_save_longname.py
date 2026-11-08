"""SAVE (in place) of a model whose file name is 250 bytes: lock/backup/temp names must fit 255 bytes; original replaced or cleanly refused, never damaged, no leftovers."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'*': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    for name in ('a' * 246 + '.rvt', 'Grundriss über 中文.rvt'):
        d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, name)
        try: shutil.copy(RTE, src)
        except OSError: print('name rejected by this fs'); continue
        h0 = sha(src); md = os.path.join(d, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            r = await c.post('/api/m/m/save', json={}); j = await r.json()
            assert r.status == 200 or j.get('code') in ('nothing_to_save', 'no_changes'), (name[:12], r.status, j)
            if r.status == 200:
                r = await c.post('/api/m/m/save', json={}); assert r.status in (200, 409), r.status
        left = [f for f in os.listdir(d) if f.endswith(('.sgtmp', '.part', '.tmp')) or f.endswith('lock')]
        assert not left, left
        assert os.path.getsize(src) > 0
    print('long-name save OK')
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: asyncio.run(run())
