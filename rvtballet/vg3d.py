"""GET /api/m/{mid}/vg3d/{vid} -> resolved graphics of a view for the 3D hidden-line style (see vg3d_worker.py). Cached per source file + view; computed by a one-shot rvt-sheets process."""
import os, sys, json, hashlib, asyncio, subprocess
from aiohttp import web
from . import vcache, plat

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS_PY = plat.sheets_py()
VER = 2 + 1


def register(app, ctx):
    locks = {}

    async def vg3d(req):
        mid, vid = req.match_info['mid'], req.match_info['vid']
        src = ctx.source_path(mid)
        if not src or not os.path.exists(src): raise web.HTTPNotFound(text='source .rvt unknown')
        key = hashlib.sha1(('%s|%s|%s|%d' % (src, os.path.getmtime(src), vid, VER)).encode()).hexdigest()[:16]
        fn = os.path.join(vcache.CACHE, 'vg3d-%s.json' % key)
        if not os.path.exists(fn):
            lk = locks.setdefault(key, asyncio.Lock())
            async with lk:
                if not os.path.exists(fn):
                    cmd = plat.proc.capped_argv([SHEETS_PY, os.path.join(HERE, 'vg3d_worker.py'), src, vid], mem_gb=4)
                    p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await p.communicate()
                    if p.returncode != 0: return web.json_response({'error': err.decode()[-400:]}, status=500)
                    os.makedirs(vcache.CACHE, exist_ok=True); tmp = fn + '.tmp%d' % os.getpid(); open(tmp, 'wb').write(out); os.replace(tmp, fn)
        return web.Response(body=open(fn, 'rb').read(), content_type='application/json')

    async def datums3d(req):
        mid = req.match_info['mid']; src = ctx.source_path(mid)
        if not src or not os.path.exists(src): raise web.HTTPNotFound(text='source .rvt unknown')
        key = hashlib.sha1(('%s|%s|datums|%d' % (src, os.path.getmtime(src), VER)).encode()).hexdigest()[:16]
        fn = os.path.join(vcache.CACHE, 'datums3d-%s.json' % key)
        if not os.path.exists(fn):
            lk = locks.setdefault(key, asyncio.Lock())
            async with lk:
                if not os.path.exists(fn):
                    cmd = plat.proc.capped_argv([SHEETS_PY, os.path.join(HERE, 'datums3d_worker.py'), src], mem_gb=4)
                    p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await p.communicate()
                    if p.returncode != 0: return web.json_response({'error': err.decode()[-400:]}, status=500)
                    os.makedirs(vcache.CACHE, exist_ok=True); tmp = fn + '.tmp%d' % os.getpid(); open(tmp, 'wb').write(out); os.replace(tmp, fn)
        return web.Response(body=open(fn, 'rb').read(), content_type='application/json')
    app.router.add_get('/api/m/{mid}/datums3d', datums3d)
    app.router.add_get('/api/m/{mid}/vg3d/{vid}', vg3d)
