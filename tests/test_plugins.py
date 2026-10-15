"""plug-in mount: a dummy module is mounted by load_plugins and sees the PluginContext (run: .venv/bin/python tests/test_plugins.py)"""
import os, sys, tempfile, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from rvtviewer import server

def test_dummy_plugin():
    d = tempfile.mkdtemp(); open(os.path.join(d, 'dummyplug.py'), 'w').write(
        "from aiohttp import web\nNAME='dummy'; TITLE='Dummy'; MOUNT='/dummy/'\ndef make_app(ctx):\n    app = web.Application()\n"
        "    async def ping(req): return web.json_response({'models': ctx.model_ids(), 'src': ctx('m1')})\n    app.router.add_get('/ping', ping); return app\n")
    sys.path.insert(0, d); os.environ['RVT_PLUGINS'] = 'dummyplug'
    models = server.Models(); md = tempfile.mkdtemp(); json.dump({'src': '/x/y.rvt'}, open(os.path.join(md, 'summary.json'), 'w')); models.add('m1', md, 'm1')
    app = server.make_app(models)
    async def run():
        async with TestClient(TestServer(app)) as c:
            r = await (await c.get('/dummy/ping')).json(); assert r == {'models': ['m1'], 'src': '/x/y.rvt'}, r
            p = await (await c.get('/api/plugins')).json(); assert p == [{'name': 'dummy', 'title': 'Dummy', 'mount': '/dummy/'}], p
    asyncio.run(run())

if __name__ == '__main__':
    test_dummy_plugin(); print('ok test_dummy_plugin')
