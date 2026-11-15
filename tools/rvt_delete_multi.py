"""Delete several element ids together in ONE SAVE AS (e.g. a column plus the tags that host on it). usage: tools/rvt_delete_multi.py FILE OUT.rvt ID[,ID...]  (prints ACCEPTED/REFUSED; accepted output written to OUT.rvt)"""
import os, sys, asyncio, tempfile, shutil
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
from rvtballet import server
async def run(f, out, ids):
    from aiohttp.test_utils import TestClient, TestServer
    src = os.path.join(_T, 's.rvt'); shutil.copy(f, src); md = os.path.join(_T, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models)), timeout=__import__('aiohttp').ClientTimeout(total=None)) as c:
        await c.get('/api/m/m/saveinfo')
        for e in ids:
            r = await c.post('/api/m/m/edit', json={'op': 'delete', 'eid': e})
            if r.status != 200: print('INPUT_REFUSED', e, (await r.text())[:300]); return 1
        r = await c.post('/api/m/m/saveas', json={'dest': out}); j = await r.json()
        if r.status == 200: print('ACCEPTED verify_unexpected=%s' % j.get('verify', {}).get('n_unexpected'), out); return 0
        print('REFUSED_%d' % r.status, j.get('code'), str(j)[:600]); return 1
if __name__ == '__main__':
    sys.exit(asyncio.run(run(sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')])))
