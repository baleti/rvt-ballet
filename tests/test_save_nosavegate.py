"""savegate not installed: viewer still starts, saveinfo says unavailable (UI disables the buttons), every save endpoint answers 501 'unavailable' - never a traceback / 500."""
import os, sys, asyncio, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import server, save
save._import = lambda: None
async def run():
    from aiohttp.test_utils import TestClient, TestServer
    t = tempfile.mkdtemp(); src = os.path.join(t, 'a.rvt'); open(src, 'wb').write(b'x' * 10); md = os.path.join(t, 'm'); os.makedirs(md)
    models = server.Models(); models.m['m'] = {'dir': md, 'name': 'a', 'src': src}
    async with TestClient(TestServer(server.make_app(models))) as c:
        i = await (await c.get('/api/m/m/saveinfo')).json(); assert i['available'] is False and i['open'] is False, i
        for path, body in (('saveas', {'dest': os.path.join(t, 'o.rvt')}), ('save', {}), ('edit', {'op': 'set_string', 'eid': 1, 'value': 'a'}), ('restore', {'confirm': True})):
            r = await c.post('/api/m/m/' + path, json=body); assert r.status == 501, (path, r.status, await r.text())
        assert await (await c.get('/api/m/m/backups')).json() == [] and await (await c.get('/api/recover')).json() == []
    print('save nosavegate OK')
asyncio.run(run())
