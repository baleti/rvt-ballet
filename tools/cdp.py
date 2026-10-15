"""Tiny headless-Chromium CDP driver for UI tests (no window is ever shown, so no workspace / focus issues)."""
import asyncio, json, os, subprocess, tempfile, time, base64, urllib.request, shutil, atexit, signal
_LIVE = set()
def _kill_all(*a):
    for b in list(_LIVE): b._kill()
atexit.register(_kill_all)
for _sg in (signal.SIGTERM, signal.SIGINT):
    try: signal.signal(_sg, lambda n, f: (_kill_all(), os._exit(1)))
    except Exception: pass
import aiohttp

class Browser:
    def __init__(self, port=9333, size=(1500, 950), gl='swiftshader'):
        self.port = port; self.size = (min(size[0], 1280), min(size[1], 720)); self.gl = gl; self.id = 0      # small viewport: swiftshader cost scales with pixels
    async def start(self):
        import socket
        sk = socket.socket(); sk.bind(('127.0.0.1', 0)); self.port = sk.getsockname()[1]; sk.close()
        self.prof = tempfile.mkdtemp(prefix='rvtv-cdp-')
        args = ['chromium', '--headless=new', '--remote-debugging-port=%d' % self.port, '--user-data-dir=' + self.prof, '--no-first-run', '--window-size=%d,%d' % self.size,
                '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', 'about:blank'] if self.gl == 'swiftshader' else \
               ['chromium', '--headless=new', '--remote-debugging-port=%d' % self.port, '--user-data-dir=' + self.prof, '--no-first-run', '--window-size=%d,%d' % self.size, '--ignore-gpu-blocklist'] + \
               ({'egl': ['--use-angle=gl-egl', '--use-gl=angle'], 'vulkan': ['--use-angle=vulkan', '--enable-features=Vulkan']}.get(self.gl, [])) + ['about:blank']      # real GPU without a window
        args = ['systemd-run', '--user', '--scope', '-q', '-p', 'CPUQuota=300%', '-p', 'MemoryMax=3G', '-p', 'MemorySwapMax=0', 'nice', '-n', '19'] + args[:1] + ['--num-raster-threads=2', '--renderer-process-limit=1'] + args[1:]      # gentle on the daily-driver host: 3 cores, 3 GB, lowest priority
        self.p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True); _LIVE.add(self)
        for _ in range(100):
            try: tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % self.port)); break
            except Exception: await asyncio.sleep(0.1)
        page = [t for t in tabs if t['type'] == 'page'][0]
        self.sess = aiohttp.ClientSession(); self.ws = await self.sess.ws_connect(page['webSocketDebuggerUrl'], max_msg_size=0)
        self.logs = []
        self._rd = asyncio.create_task(self._reader()); self.waiters = {}
        await self.call('Page.enable'); await self.call('Runtime.enable')
        await self.call('Emulation.setDeviceMetricsOverride', width=self.size[0], height=self.size[1], deviceScaleFactor=1, mobile=False)
    async def _reader(self):
        async for m in self.ws:
            d = json.loads(m.data)
            if 'id' in d and d['id'] in self.waiters: self.waiters.pop(d['id']).set_result(d)
            elif d.get('method') == 'Runtime.consoleAPICalled': self.logs.append(' '.join(str(a.get('value', a.get('description', ''))) for a in d['params']['args']))
            elif d.get('method') == 'Runtime.exceptionThrown': self.logs.append('EXC ' + json.dumps(d['params']['exceptionDetails'])[:600])
    async def call(self, method, **params):
        self.id += 1; f = asyncio.get_event_loop().create_future(); self.waiters[self.id] = f
        await self.ws.send_str(json.dumps({'id': self.id, 'method': method, 'params': params})); r = await f
        if 'error' in r: raise RuntimeError(r['error'])
        return r.get('result')
    async def goto(self, url): await self.call('Page.navigate', url=url)
    async def ev(self, js):
        r = await asyncio.wait_for(self.call('Runtime.evaluate', expression=js, awaitPromise=True, returnByValue=True), 30)
        if 'exceptionDetails' in r: raise RuntimeError(json.dumps(r['exceptionDetails'])[:500])
        return r['result'].get('value')
    async def wait(self, js, timeout=120):
        t = time.time()
        while time.time() - t < timeout:
            try:
                if await self.ev(js): return True
            except Exception: pass
            await asyncio.sleep(0.3)
        raise TimeoutError(js)
    async def click(self, x, y, button='left', mods=0, count=1):
        for t in ('mouseMoved', 'mousePressed', 'mouseReleased'):
            await self.call('Input.dispatchMouseEvent', type=t, x=x, y=y, button=button if t != 'mouseMoved' else 'none', clickCount=count, modifiers=mods)
    async def drag(self, x0, y0, x1, y1, button='left', steps=8, mods=0):
        mask = {'left': 1, 'right': 2, 'middle': 4}[button]
        await self.call('Input.dispatchMouseEvent', type='mouseMoved', x=x0, y=y0)
        await self.call('Input.dispatchMouseEvent', type='mousePressed', x=x0, y=y0, button=button, clickCount=1, buttons=mask, modifiers=mods)
        for k in range(1, steps + 1):
            await self.call('Input.dispatchMouseEvent', type='mouseMoved', x=x0 + (x1 - x0) * k / steps, y=y0 + (y1 - y0) * k / steps, button=button, buttons=mask, modifiers=mods)
        await self.call('Input.dispatchMouseEvent', type='mouseReleased', x=x1, y=y1, button=button, clickCount=1, modifiers=mods)
    async def wheel(self, x, y, dy):
        await self.call('Input.dispatchMouseEvent', type='mouseWheel', x=x, y=y, deltaX=0, deltaY=dy)
    async def key(self, k):
        kw = {'text': k} if len(k) == 1 else {}; await self.call('Input.dispatchKeyEvent', type='keyDown', key=k, **kw); await self.call('Input.dispatchKeyEvent', type='keyUp', key=k)
    async def shot(self, path):
        r = await self.call('Page.captureScreenshot', format='png', fromSurface=getattr(self, 'from_surface', True)); open(path, 'wb').write(base64.b64decode(r['data']))
    def _kill(self):
        try: os.killpg(self.p.pid, signal.SIGKILL)
        except Exception: pass
        try: self.p.wait(timeout=2)
        except Exception: pass
        shutil.rmtree(getattr(self, 'prof', ''), ignore_errors=True); _LIVE.discard(self)
    async def close(self):
        try: await self.call('Browser.close')
        except Exception: pass
        try: await self.sess.close()
        finally: self._kill()

def wait_http(url, timeout=30):
    t = time.time()
    while time.time() - t < timeout:
        try: urllib.request.urlopen(url, timeout=2).read(); return
        except Exception: time.sleep(0.2)
    raise TimeoutError(url)
