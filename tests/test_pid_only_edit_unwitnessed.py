"""an edit addressed by parameter id only whose result the reader view cannot show must be refused at save (value unverifiable); the visible pid still saves. Autodesk-derived sample needed: skipped when absent."""
import os, sys, shutil, tempfile, asyncio, pytest
SRC = '/srv/tank/remote-host-archive/2026-11-01/wl-push/e1_level_2026.rte'
@pytest.mark.skipif(not os.path.exists(SRC), reason='sample missing')
def test_pid_only_unwitnessed_refused():
    T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = '0'
    import json; json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
    sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    import aiohttp
    from rvtballet import server
    from aiohttp.test_utils import TestClient, TestServer
    src = T + '/p.rvt'; shutil.copy(SRC, src)
    async def run():
        models = server.Models(); models.m['m'] = {'dir': tempfile.mkdtemp(dir=T), 'name': 'a', 'src': src}; out = {}
        async with TestClient(TestServer(server.make_app(models))) as c:
            await c.get('/api/m/m/saveinfo')
            for pid in (-1150481, -1010103):
                r = await c.post('/api/m/m/edit', json={'op': 'set_string', 'eid': 1247, 'pid': pid, 'value': 'Q' * 27})
                assert r.status == 200
                r = await c.post('/api/m/m/saveas', json={'dest': T + '/o%d.rvt' % -pid}, timeout=aiohttp.ClientTimeout(total=None)); out[pid] = (r.status, await r.json())
                await c.post('/api/m/m/edit/undo')
        return out
    out = asyncio.run(run())
    assert out[-1150481][0] == 422 and 'cannot be verified' in out[-1150481][1]['error'], out[-1150481]
    assert out[-1010103][0] == 200, out[-1010103]
    assert not os.path.exists(T + '/o1150481.rvt')
