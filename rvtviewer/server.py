"""Local HTTP server: static front-end + per-model cache files + lazy metadata / search API."""
import os, json, sqlite3, asyncio, gzip, re
from aiohttp import web

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web')

class Models:
    def __init__(self): self.m = {}       # id -> dict(dir, name)
    def add(self, mid, d, name, building=False): self.m[mid] = {'dir': d, 'name': name, 'db': None, 'building': building}
    def db(self, mid):
        m = self.m[mid]
        if m['db'] is None:
            m['db'] = sqlite3.connect(os.path.join(m['dir'], 'model.sqlite'), check_same_thread=False)
            m['db'].row_factory = sqlite3.Row
        return m['db']

def make_app(models):
    app = web.Application(client_max_size=1 << 20)
    @web.middleware
    async def nocache(req, handler):
        resp = await handler(req)
        resp.headers['Cache-Control'] = 'no-cache'
        return resp
    app.middlewares.append(nocache)
    async def index(req): return web.FileResponse(os.path.join(WEB, 'index.html'))
    async def list_models(req): return web.json_response([{'id': k, 'name': v['name'], 'building': v.get('building', False)} for k, v in models.m.items()])
    def mdir(req):
        mid = req.match_info['mid']
        if mid not in models.m: raise web.HTTPNotFound()
        return mid, models.m[mid]['dir']
    async def meta(req):
        mid, d = mdir(req); fn = os.path.join(d, 'meta.json')
        if not os.path.exists(fn): raise web.HTTPNotFound()
        return web.FileResponse(fn)
    async def glb(req):
        mid, d = mdir(req); return web.FileResponse(os.path.join(d, 'model.glb'))
    async def preview(req):
        mid, d = mdir(req); return web.FileResponse(os.path.join(d, 'preview.glb'))
    async def progress(req):
        mid, d = mdir(req); fn = os.path.join(d, 'progress.json')
        try: return web.json_response(json.load(open(fn)))
        except Exception: return web.json_response({'stage': 'starting', 'stages': ['reading', 'tables', 'preview', 'geometry', 'packing', 'done'], 'pct': 0, 'msg': 'starting', 'elapsed': 0})
    async def element(req):
        mid, d = mdir(req); i = int(req.match_info['i']); db = models.db(mid)
        row = db.execute('select * from el where i=?', (i,)).fetchone()
        if not row: raise web.HTTPNotFound()
        prm = [(r['k'], r['v']) for r in db.execute('select k,v from prm where i=? order by k', (i,))]
        return web.json_response({'el': dict(row), 'params': prm})
    async def search(req):
        """parameter-value / name search: ?q=text[&limit=500]; returns element indices with the matching parameter"""
        mid, d = mdir(req); q = req.query.get('q', '').strip(); lim = int(req.query.get('limit', 2000)); db = models.db(mid)
        if not q: return web.json_response([])
        like = '%' + q.replace('%', r'\%').replace('_', r'\_') + '%'
        rows = db.execute("select i,k,v from prm where v like ? escape '\\' limit ?", (like, lim)).fetchall()
        out = {}
        for r in rows: out.setdefault(r['i'], []).append([r['k'], r['v']])
        return web.json_response([[i, v[:3]] for i, v in out.items()])
    app.router.add_get('/', index)
    app.router.add_get('/api/models', list_models)
    app.router.add_get('/m/{mid}/meta.json', meta)
    app.router.add_get('/m/{mid}/model.glb', glb)
    app.router.add_get('/m/{mid}/preview.glb', preview)
    app.router.add_get('/api/m/{mid}/progress', progress)
    app.router.add_get('/api/m/{mid}/el/{i}', element)
    app.router.add_get('/api/m/{mid}/search', search)
    app.router.add_static('/', WEB, follow_symlinks=False)
    return app

def serve(models, host='127.0.0.1', port=0, ready=None):
    app = make_app(models)
    async def run():
        runner = web.AppRunner(app); await runner.setup()
        site = web.TCPSite(runner, host, port); await site.start()
        p = site._server.sockets[0].getsockname()[1]
        if ready: ready(p)
        while True: await asyncio.sleep(3600)
    asyncio.run(run())
