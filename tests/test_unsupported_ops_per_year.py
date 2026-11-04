"""add/copy/create/duplicate/mirror/array edit ops are refused with 4xx and the file stays byte-identical, one smallest local corpus file per Revit year 2017-2026 (skip years absent). Never touches the real gate."""
import os, sys, asyncio, tempfile, hashlib, shutil, json, glob
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import server, save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
OPS = ['copy', 'add', 'create', 'duplicate', 'mirror', 'array', 'paste', 'new', 'insert', 'place', 'COPY', '', None]
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    n = bad = 0
    for y in range(2017, 2027):
        fs = sorted(glob.glob(os.path.expanduser('~/rvtfix/corpus/%d/*' % y)), key=os.path.getsize)
        if not fs: print(y, 'absent'); continue
        src = os.path.join(_T, 's%d.rvt' % y); shutil.copy(fs[0], src); h0 = sha(src); md = os.path.join(_T, 'm%d' % y); os.makedirs(md)
        models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        ok = 0
        async with TestClient(TestServer(server.make_app(models))) as c:
            for op in OPS:
                r = await c.post('/api/m/m/edit', json={'op': op, 'eid': 1, 'dx': 1.0, 'dy': 0, 'dz': 0}); n += 1
                if 400 <= r.status < 500: ok += 1
                else: bad += 1; print('BAD', y, op, r.status)
        assert sha(src) == h0, 'source changed %d' % y
        print(y, 'refused %d/%d, source untouched' % (ok, len(OPS)))
    assert not bad, bad
    print('unsupported ops per year OK %d posts' % n)
asyncio.run(run())
