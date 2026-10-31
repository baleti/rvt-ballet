"""Per Revit year 2017..2026 (stub = real 2024 scene with BasicFileInfo year rewritten): writable years save, others are refused with a message naming
the version and the writable list (HTTP 415), saveinfo reports open=false + the same text (UI disables the buttons), nothing is written."""
import os, sys, asyncio, tempfile
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WL = os.path.expanduser('~/rvt-research/write-lab'); RTE = WL + '/scenes/classtests/2024_writer_cols2.rte'
from rvtballet import server, save

def stub(year, path):
    sys.path.insert(0, WL); import cfb
    c = cfb.CFB(open(RTE, 'rb').read()); e = c.streams()['BasicFileInfo']
    assert '2024'.encode('utf-16le') in e.data
    e.data = e.data.replace('2024'.encode('utf-16le'), str(year).encode('utf-16le'), 1)
    import re      # the build stamp (YYYYMMDD_HHMM) moves with the year too: savegate refuses a year that is more than 2 years away from its build stamp (relabelled files)
    t = e.data.decode('utf-16le', 'ignore'); t2 = re.sub(r'(20[12]\d)([01]\d[0-3]\d_\d{4})', lambda m: str(year) + m.group(2), t, count=1)
    if t2 != t: e.data = t2.encode('utf-16le')
    cfb.write(c, path)

async def run():
    from aiohttp.test_utils import TestClient, TestServer
    res = {}
    for year in range(2017, 2027):
        d = os.path.join(_T, str(year)); os.makedirs(d); src = os.path.join(d, 'a.rvt'); stub(year, src)
        md = os.path.join(d, 'm'); os.makedirs(md); models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
        dest = os.path.join(d, 'out.rvt')
        async with TestClient(TestServer(server.make_app(models))) as c:
            i = await (await c.get('/api/m/m/saveinfo')).json()
            r = await c.post('/api/m/m/saveas', json={'dest': dest}); j = await r.json()
        w = str(year) in ('2024', '2026')
        if w: assert r.status == 200 and i['open'] and i['version'] == str(year) and os.path.exists(dest), (year, r.status, j, i)
        else:
            assert r.status == 415 and j['code'] == 'unsupported_version' and str(year) in j['error'] and '2024, 2026' in j['error'], (year, r.status, j)
            assert i['open'] is False and str(year) in i['error'] and not os.path.exists(dest) and not any('sgtmp' in f for f in os.listdir(d)), (year, i)
        res[year] = r.status
    print('save versions OK', res)

if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip: savegate or scene missing')
else: asyncio.run(run())
