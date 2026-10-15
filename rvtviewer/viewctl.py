"""View control API (CONTROL-API.md): view-dependent drawing content (tags, text, dimensions, grids, levels, markers, hatches, linework) of a
plan / section / drafting view as JSON primitives with element + category tables, so the front-end can place it in model space and control it
per category / element. The drawing code is rvt-sheets (run in its own venv, one worker process per model, results cached on disk).
  GET /api/m/{mid}/vc/views                      -> views of the file
  GET /api/m/{mid}/vc/scene/{vid}?scale=&detail=&template=0|1&filters=0|1   -> scene (see vscene_worker.py)
  GET /api/m/{mid}/vc/element/{eid}              -> raw stored fields of one element
  GET|PUT /api/vc/presets                        -> saved control presets (~/.config/rvt-viewer/vctl-presets.json)"""
import os, sys, json, hashlib, asyncio, subprocess, threading, time
from aiohttp import web
from . import vcache

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS_PY = os.environ.get('RVT_SHEETS_PY', os.path.expanduser('~/src/rvt-sheets/.venv/bin/python'))
CACHE = vcache.CACHE
PRESETS = os.path.expanduser('~/.config/rvt-viewer/vctl-presets.json')
IDLE = 600


class Proc:
    """one worker process per source file; requests are serialised; killed after IDLE seconds without use"""
    def __init__(self, path):
        self.path = path; self.p = None; self.lock = threading.Lock(); self.last = time.time(); self.key = None

    def _start(self):
        cmd = ['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=4G', '-p', 'MemorySwapMax=0', 'nice', '-n', '10', SHEETS_PY, os.path.join(HERE, 'vscene_worker.py'), self.path]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        r = json.loads(self.p.stdout.readline()); self.key = r.get('key')

    def call(self, req):
        with self.lock:
            if self.p is None or self.p.poll() is not None: self._start()
            self.last = time.time()
            self.p.stdin.write(json.dumps(req) + '\n'); self.p.stdin.flush()
            line = self.p.stdout.readline()
            if not line: self.p = None; raise RuntimeError('scene worker died')
            self.last = time.time()
            return line

    def reap(self):
        with self.lock:
            if self.p and self.p.poll() is None and time.time() - self.last > IDLE: self.p.terminate(); self.p = None


def register(app, ctx):
    procs = {}

    def proc(mid):
        src = ctx.source_path(mid)
        if not src or not os.path.exists(src): raise web.HTTPNotFound(text='source .rvt of model %s unknown' % mid)
        if src not in procs: procs[src] = Proc(src)
        return procs[src], src

    async def run(mid, req, use_cache):
        pr, src = proc(mid)
        fn = vcache.cache_fn(src, req) if use_cache else None
        if fn and os.path.exists(fn): return open(fn, 'rb').read()
        line = await asyncio.get_running_loop().run_in_executor(None, pr.call, req)
        if fn and '"error"' not in line[:20]:
            os.makedirs(CACHE, exist_ok=True); tmp = fn + '.tmp%d' % os.getpid(); open(tmp, 'w').write(line); os.replace(tmp, fn)
        return line.encode()

    async def views(req):
        return web.Response(body=await run(req.match_info['mid'], {'op': 'views'}, True), content_type='application/json')

    async def scene(req):
        q = req.query; r = {'op': 'scene', 'view': int(req.match_info['vid'])}
        if q.get('scale'): r['scale'] = int(q['scale'])
        if q.get('detail'): r['detail'] = int(q['detail'])
        if q.get('cut'): r['cut'] = float(q['cut'])
        if q.get('phase'): r['phase'] = int(q['phase'])
        if q.get('phaseFilter'): r['phaseFilter'] = int(q['phaseFilter'])
        if q.get('template') == '0': r['template'] = False
        if q.get('filters') == '0': r['filters'] = False
        try: body = await run(req.match_info['mid'], r, True)
        except web.HTTPException: raise
        except Exception as ex: return web.json_response({'error': str(ex)}, status=500)
        return web.Response(body=body, content_type='application/json')

    async def element(req):
        return web.Response(body=await run(req.match_info['mid'], {'op': 'element', 'id': int(req.match_info['eid'])}, True), content_type='application/json')

    async def presets_get(req):
        try: return web.json_response(json.load(open(PRESETS)))
        except Exception: return web.json_response({})

    async def presets_put(req):
        d = await req.json()
        os.makedirs(os.path.dirname(PRESETS), exist_ok=True); tmp = PRESETS + '.tmp'; json.dump(d, open(tmp, 'w'), indent=1); os.replace(tmp, PRESETS)
        return web.json_response({'ok': True})

    app.router.add_get('/api/m/{mid}/vc/views', views)
    app.router.add_get('/api/m/{mid}/vc/scene/{vid}', scene)
    app.router.add_get('/api/m/{mid}/vc/element/{eid}', element)
    app.router.add_get('/api/vc/presets', presets_get); app.router.add_put('/api/vc/presets', presets_put)

    async def reaper(app_):
        async def loop():
            while True:
                await asyncio.sleep(60)
                for p in list(procs.values()): p.reap()
        t = asyncio.create_task(loop()); yield; t.cancel()
    app.cleanup_ctx.append(reaper)
