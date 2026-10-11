"""Tiny headless-Chromium CDP driver for UI tests (no window is ever shown, so no workspace / focus issues)."""
import asyncio, json, os, subprocess, tempfile, time, base64, urllib.request, shutil
import aiohttp

class Browser:
    def __init__(self, port=9333, size=(1500, 950), gl='swiftshader'):
        self.port = port; self.size = size; self.gl = gl; self.id = 0
    async def start(self):
        self.prof = tempfile.mkdtemp(prefix='rvtv-cdp-')
        args = ['chromium', '--headless=new', '--remote-debugging-port=%d' % self.port, '--user-data-dir=' + self.prof, '--no-first-run', '--window-size=%d,%d' % self.size,
                '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', 'about:blank'] if self.gl == 'swiftshader' else \
               ['chromium', '--headless=new', '--remote-debugging-port=%d' % self.port, '--user-data-dir=' + self.prof, '--no-first-run', '--window-size=%d,%d' % self.size, '--ignore-gpu-blocklist', 'about:blank']
        self.p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        r = await self.call('Runtime.evaluate', expression=js, awaitPromise=True, returnByValue=True)
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
    async def drag(self, x0, y0, x1, y1, button='left', steps=8):
        await self.call('Input.dispatchMouseEvent', type='mouseMoved', x=x0, y=y0)
        await self.call('Input.dispatchMouseEvent', type='mousePressed', x=x0, y=y0, button=button, clickCount=1, buttons=1 if button == 'left' else 2)
        for k in range(1, steps + 1):
            await self.call('Input.dispatchMouseEvent', type='mouseMoved', x=x0 + (x1 - x0) * k / steps, y=y0 + (y1 - y0) * k / steps, button=button, buttons=1 if button == 'left' else 2)
        await self.call('Input.dispatchMouseEvent', type='mouseReleased', x=x1, y=y1, button=button, clickCount=1)
    async def wheel(self, x, y, dy):
        await self.call('Input.dispatchMouseEvent', type='mouseWheel', x=x, y=y, deltaX=0, deltaY=dy)
    async def key(self, k):
        await self.call('Input.dispatchKeyEvent', type='keyDown', key=k, text=k); await self.call('Input.dispatchKeyEvent', type='keyUp', key=k)
    async def shot(self, path):
        r = await self.call('Page.captureScreenshot', format='png'); open(path, 'wb').write(base64.b64decode(r['data']))
    async def close(self):
        try: await self.call('Browser.close')
        except Exception: pass
        self.p.terminate(); await self.sess.close(); shutil.rmtree(self.prof, ignore_errors=True)
