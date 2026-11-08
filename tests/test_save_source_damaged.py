"""A source with a provably CRC-bad gzip member (one stored CRC32 byte flipped in a Partitions/* stream of an Autodesk 2024 template) is refused by
SAVE AS and SAVE with code 'source_damaged', nothing written, source untouched; the undamaged template still saves (identity)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, asyncio, tempfile, hashlib, shutil, json, zlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
from rvtballet import server, save
from rvtballet.edit import WL
sys.path.insert(0, WL); import cfb, rvtw
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

def damage(src, dst):
    c = cfb.CFB(open(src, 'rb').read())
    for k, e in c.streams().items():
        if not k.startswith('Partitions/'): continue
        s = rvtw.Stream(e.data); P = bytearray(s.payload); pos = P.find(rvtw.GZ)
        if pos < 0: continue
        do = zlib.decompressobj(-15); do.decompress(bytes(P[pos + 10:]))
        end = len(P) - len(do.unused_data) + 8
        P[end - 5] ^= 1          # a CRC32 byte of the trailer
        e.data = s.build(bytes(P)); cfb.write(c, dst); return k
    raise AssertionError('no partition with a gzip member')
assert not save.source_damage(open(SRC, 'rb').read()), 'clean template reported damaged'
bad = os.path.join(_T, 'bad.rte'); k = damage(SRC, bad)
assert save.source_damage(open(bad, 'rb').read()), 'damage not detected'

async def run():
    from aiohttp.test_utils import TestClient, TestServer
    md = os.path.join(_T, 'm'); os.makedirs(md); h0 = sha(bad)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': bad}
    async with TestClient(TestServer(server.make_app(models))) as c:
        out = os.path.join(_T, 'o.rte')
        r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        assert r.status == 409 and j.get('code') == 'source_damaged', (r.status, j)
        assert not os.path.exists(out)
        r = await c.post('/api/m/m/save', json={}); j = await r.json()
        assert r.status == 409 and j.get('code') == 'source_damaged', (r.status, j)
    assert sha(bad) == h0 and not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]
    good = os.path.join(_T, 'good.rte'); shutil.copy(SRC, good); models.m['g'] = {'dir': md, 'name': 'g', 'src': good}
    async with TestClient(TestServer(server.make_app(models))) as c:
        r = await c.post('/api/m/g/saveas', json={'dest': os.path.join(_T, 'g2.rte')}); assert r.status == 200, r.status
        assert sha(os.path.join(_T, 'g2.rte')) == sha(good)
asyncio.run(run()); print('OK source_damaged (stream %s)' % k)
