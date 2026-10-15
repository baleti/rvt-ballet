"""Local HTTP server: static front-end + per-model cache files + lazy metadata / search API."""
import os, json, sqlite3, asyncio, gzip, re
from aiohttp import web

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web')

class Models:
    def __init__(self): self.m = {}       # id -> dict(dir, name)
    def add(self, mid, d, name, building=False):
        cached = False
        if not building:
            try: cached = json.load(open(os.path.join(d, 'meta.json'))).get('phase') == 'done'
            except Exception: pass
        self.m[mid] = {'dir': d, 'name': name, 'db': None, 'building': building, 'cached': cached}
    def db(self, mid):
        m = self.m[mid]
        if m['db'] is None:
            m['db'] = sqlite3.connect(os.path.join(m['dir'], 'model.sqlite'), check_same_thread=False)
            m['db'].row_factory = sqlite3.Row
        return m['db']

class PluginContext:
    """what a plug-in sees of the viewer (documented in docs/PLUGINS.md). Callable: ctx(mid) -> path of the source .rvt (the `model_dir_resolver` of HOOKS.md)."""
    def __init__(self, models): self.models = models
    def __call__(self, mid): return self.source_path(mid)
    def model_ids(self): return list(self.models.m)
    def model_dir(self, mid):
        if mid not in self.models.m: raise KeyError(mid)
        return self.models.m[mid]['dir']
    def source_path(self, mid):
        """absolute path of the .rvt a model id was converted from (None if unknown)"""
        m = self.models.m.get(mid) or {}
        if m.get('src'): return m['src']
        try: return json.load(open(os.path.join(m['dir'], 'summary.json'))).get('src')
        except Exception: return None
    def meta(self, mid):
        """meta.json of the model (levels, grids, views, sheets, elements rows [id, class, category, name, type, level, fid, isType, family, phase], ...)"""
        return json.load(open(os.path.join(self.model_dir(mid), 'meta.json')))
    def sqlite(self, mid): return self.models.db(mid)           # tables el(i,id,cls,cat,name,type,family,level,uid,ifc,fid,bb,iou,type_i), prm(i,k,v), ginfo(i,info)
    def element_index(self, mid, element_id):
        """viewer element index (position in meta.elements) of a Revit element id, or None"""
        r = self.models.db(mid).execute('select i from el where id=?', (int(element_id),)).fetchone(); return None if r is None else r[0]
    @property
    def reader(self):
        """rvtviewer.reader: _import() puts ~/rvt-research on sys.path (rvt_geometry, rvt_elemmesh, rvt_materials, ...), cached_load(path), reader_stamp()"""
        from . import reader; return reader


def load_plugins(app, models):
    """mount viewer plug-ins as aiohttp sub-apps. A plug-in is a python module with make_app(ctx) -> aiohttp.web.Application and optional NAME / TITLE / MOUNT ('/sheets/').
    Sources: env RVT_PLUGINS (comma list of module names), ~/.config/rvt-viewer/plugins.json ({"plugins": [{"module": "rvtsheets.server", "path": "~/src/rvt-sheets", "mount": "/sheets/", "title": "Sheets"}]}),
    and the built-in default rvtsheets.server from ~/src/rvt-sheets when that directory exists."""
    import importlib, sys
    cfg = []
    for n in filter(None, os.environ.get('RVT_PLUGINS', '').split(',')): cfg.append({'module': n.strip()})
    f = os.path.expanduser('~/.config/rvt-viewer/plugins.json')
    if os.path.exists(f):
        try: cfg += json.load(open(f)).get('plugins', [])
        except Exception as ex: print('plugins.json unreadable:', ex)
    if not cfg and os.path.isdir(os.path.expanduser('~/src/rvt-sheets/rvtsheets')): cfg.append({'module': 'rvtsheets.server', 'path': '~/src/rvt-sheets', 'mount': '/sheets/', 'title': 'Sheets'})
    ctx = PluginContext(models); loaded = []
    for c in cfg:
        try:
            if c.get('path') and os.path.expanduser(c['path']) not in sys.path: sys.path.insert(0, os.path.expanduser(c['path']))
            mod = importlib.import_module(c['module']); mount = c.get('mount') or getattr(mod, 'MOUNT', None) or '/' + c['module'].split('.')[0] + '/'
            if not mount.endswith('/'): mount += '/'
            app.add_subapp(mount, mod.make_app(ctx))
            loaded.append({'name': getattr(mod, 'NAME', c['module']), 'title': c.get('title') or getattr(mod, 'TITLE', c['module']), 'mount': mount})
        except Exception as ex:
            print('plug-in %s not loaded: %r' % (c.get('module'), ex))
            hint = ' (pip install shapely numba in the viewer venv)' if isinstance(ex, ImportError) else ''
            loaded.append({'name': c['module'], 'title': c.get('title') or c['module'], 'mount': c.get('mount') or '', 'error': '%s: %s%s' % (type(ex).__name__, ex, hint)})
    return loaded


def make_app(models):
    app = web.Application(client_max_size=1 << 20)
    @web.middleware
    async def nocache(req, handler):
        resp = await handler(req)
        resp.headers['Cache-Control'] = 'no-cache'
        return resp
    app.middlewares.append(nocache)
    async def index(req): return web.FileResponse(os.path.join(WEB, 'index.html'))
    async def list_models(req): return web.json_response([{'id': k, 'name': v['name'], 'building': v.get('building', False), 'cached': v.get('cached', False)} for k, v in models.m.items()])
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
    async def compare(req):
        mid, d = mdir(req); fn = os.path.join(d, 'compare.json')
        if not os.path.exists(fn): raise web.HTTPNotFound()
        return web.FileResponse(fn)
    async def progress(req):
        mid, d = mdir(req); fn = os.path.join(d, 'progress.json')
        try: return web.json_response(json.load(open(fn)))
        except Exception: return web.json_response({'stage': 'starting', 'stages': ['reading', 'tables', 'preview', 'geometry', 'packing', 'done'], 'pct': 0, 'msg': 'starting', 'elapsed': 0})
    async def element(req):
        mid, d = mdir(req); i = int(req.match_info['i'])
        try: db = models.db(mid)
        except Exception: return web.json_response({'el': {}, 'params': [], 'typeParams': [], 'ginfo': None, 'materials': [], 'pending': True})      # tables not written yet (quick preview)
        row = db.execute('select * from el where i=?', (i,)).fetchone()
        if not row: raise web.HTTPNotFound()
        prm = [(r['k'], r['v']) for r in db.execute('select k,v from prm where i=? order by k', (i,))]
        tp = []
        if row['type_i'] is not None and row['type_i'] != i: tp = [(r['k'], r['v']) for r in db.execute('select k,v from prm where i=? order by k', (row['type_i'],))]
        gi = None
        try:
            g_ = db.execute('select info from ginfo where i=?', (i,)).fetchone(); gi = json.loads(g_[0]) if g_ else None
        except Exception: pass
        mats = []
        try: mats = [r[0] for r in db.execute('select distinct m from elmat where i=?', (i,))]
        except Exception: pass
        return web.json_response({'el': dict(row), 'params': prm, 'typeParams': tp, 'ginfo': gi, 'materials': mats})
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
    async def reader_info(req):
        from . import reader
        return web.json_response({'reader': reader.reader_stamp(), 'viewer': reader.viewer_stamp(), 'geometryApi': os.path.exists(os.path.join(reader.READER_DIR, 'GEOMETRY_API.md'))})
    async def reconvert(req):
        mid = req.match_info['mid']; cb = getattr(models, 'reconvert', None)
        new = cb(mid) if cb else None
        return web.json_response({'ok': bool(new), 'id': new})
    async def library(req):
        """every converted model in the cache (summary.json per model), flagged stale if the reader/converter changed since"""
        from . import reader
        root = os.path.join(reader.CACHE_DIR, 'models'); out = []; rs, vs = reader.reader_stamp(), reader.viewer_stamp()
        for n in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            d = os.path.join(root, n)
            if n.endswith('.tmp') or not os.path.exists(os.path.join(d, 'meta.json')): continue
            fn = os.path.join(d, 'summary.json')
            if not os.path.exists(fn):
                try:
                    m = json.load(open(os.path.join(d, 'meta.json'))); from .build import write_summary; write_summary(d, m)
                except Exception: continue
            sm = json.load(open(fn)); st = sm.get('stamps') or {}
            out.append({'id': n, 'stale': st.get('reader') != rs or st.get('viewer') != vs, 'loaded': n in models.m, **sm})
        out.sort(key=lambda x: -(x.get('built') or 0)); return web.json_response(out)
    async def open_path(req):
        body = await req.json(); path = os.path.expanduser(body.get('path', ''))
        if not os.path.isfile(path): return web.json_response({'ok': False, 'error': 'file not found: ' + path})
        cb = getattr(models, 'open_path', None); mid = cb(path) if cb else None
        return web.json_response({'ok': bool(mid), 'id': mid})
    async def load_id(req):
        from . import reader
        body = await req.json(); n = body.get('id', ''); d = os.path.join(reader.CACHE_DIR, 'models', os.path.basename(n))
        if not os.path.exists(os.path.join(d, 'meta.json')): return web.json_response({'ok': False})
        if n not in models.m: models.add(n, d, n.rsplit('-', 1)[0])
        return web.json_response({'ok': True, 'id': n})
    app.router.add_get('/api/library', library); app.router.add_post('/api/open', open_path); app.router.add_post('/api/load', load_id)
    app.router.add_get('/api/reader', reader_info)
    app.router.add_post('/api/m/{mid}/reconvert', reconvert)
    app.router.add_get('/m/{mid}/model.glb', glb)
    app.router.add_get('/m/{mid}/preview.glb', preview)
    app.router.add_get('/api/m/{mid}/progress', progress)
    app.router.add_get('/m/{mid}/compare.json', compare)
    async def materials_json(req):
        mid, d = mdir(req); fn = os.path.join(d, 'materials.json')
        if not os.path.exists(fn): raise web.HTTPNotFound()
        return web.FileResponse(fn)
    async def material_elements(req):
        mid, d = mdir(req); k = int(req.match_info['k'])
        try: return web.json_response([r[0] for r in models.db(mid).execute('select distinct i from elmat where m=?', (k,))])
        except Exception: return web.json_response([])
    async def mat_image(req):
        mid, d = mdir(req); kind = req.match_info['kind']; k = req.match_info['k']
        if kind not in ('swatch', 'tex', 'bump') or not k.isdigit(): raise web.HTTPNotFound()
        fn = os.path.join(d, kind, k + '.png')
        if not os.path.exists(fn): raise web.HTTPNotFound()
        return web.FileResponse(fn, headers={'Cache-Control': 'max-age=3600'})
    app.router.add_get('/m/{mid}/{kind}/{k}.png', mat_image)
    app.router.add_get('/m/{mid}/materials.json', materials_json)
    app.router.add_get('/api/m/{mid}/material/{k}', material_elements)
    app.router.add_get('/api/m/{mid}/el/{i}', element)
    app.router.add_get('/api/m/{mid}/search', search)
    plugins = load_plugins(app, models)
    try:
        from . import viewctl; viewctl.register(app, PluginContext(models))
    except Exception as ex: print('view control not loaded: %r' % ex)
    async def list_plugins(req): return web.json_response(plugins)
    app.router.add_get('/api/plugins', list_plugins)
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
