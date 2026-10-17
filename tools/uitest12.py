"""Revit navigation with real input events: middle-drag pans, Shift+middle-drag orbits, right-drag does nothing, wheel zooms, plain left-drag does not move the camera, Alt+left orbits,
Alt+Shift+left pans, double middle-click fits. usage: tools/uitest12.py MODELDIR PORT OUT"""
import asyncio, sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, out):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-viewer'), 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1500, 900)); await b.start(); ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name)
    cam = lambda: b.ev("JSON.stringify([...__camera.position.toArray(), ...__controls.target.toArray()])")
    async def moved(fn):
        import json
        async def settle():      # damping keeps the camera moving for a few frames (slow software GL): wait until two reads agree
            prev = None
            for _ in range(40):
                cur = await cam()
                if cur == prev: return
                prev = cur; await asyncio.sleep(0.6)
        await settle(); a = json.loads(await cam()); await fn(); await settle(); c = json.loads(await cam())
        dpos = sum((x - y) ** 2 for x, y in zip(a[:3], c[:3])) ** .5; dtar = sum((x - y) ** 2 for x, y in zip(a[3:], c[3:])) ** .5; return dpos, dtar
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(1.0)
        await b.ev('__controls.enableDamping=false; 0')      # no inertia: the test measures what each input moves
        x, y = 700, 450
        SHIFT, ALT = 8, 1
        dp, dt = await moved(lambda: b.drag(x, y, x + 120, y + 40, button='middle')); chk('middle-drag pans (target moves) %.2f %.2f' % (dp, dt), dt > 0.05)
        dp, dt = await moved(lambda: b.drag(x, y, x + 120, y + 40, button='middle', mods=SHIFT)); chk('shift+middle-drag orbits (target fixed, camera moves) %.2f %.2f' % (dp, dt), dp > 0.05 and dt < 0.05)
        dp, dt = await moved(lambda: b.drag(x, y, x + 120, y + 40, button='right')); chk('right-drag does nothing %.3f %.3f' % (dp, dt), dp < 1e-3 and dt < 1e-3)
        dp, dt = await moved(lambda: b.drag(x, y, x + 120, y + 40, button='left')); chk('plain left-drag does not move the camera %.3f %.3f' % (dp, dt), dp < 1e-3 and dt < 1e-3)
        dp, dt = await moved(lambda: b.drag(x, y, x + 120, y + 40, button='left', mods=ALT)); chk('alt+left-drag orbits %.2f %.2f' % (dp, dt), dp > 0.05 and dt < 0.05)
        dp, dt = await moved(lambda: b.drag(x, y, x + 120, y + 40, button='left', mods=ALT | SHIFT)); chk('alt+shift+left-drag pans %.2f %.2f' % (dp, dt), dt > 0.05)
        dp, dt = await moved(lambda: b.wheel(x, y, -300)); chk('wheel zooms %.2f' % dp, dp > 0.05)
        async def dbl():
            await b.click(x, y, button='middle'); await asyncio.sleep(0.12); await b.click(x, y, button='middle')
        before = await cam(); dp, dt = await moved(dbl); chk('double middle-click fits (camera returns to the fit view) %.2f' % dp, dp > 0.05 and not await b.ev("document.querySelector('#viewbar').hidden===false"))
        chk('no console errors', not [l for l in b.logs if 'rror' in l])
    finally: await b.close(); srv.terminate()
    print('ALL OK' if ok else 'SOME FAILED')
asyncio.run(main(*sys.argv[1:3][:1], int(sys.argv[2]), sys.argv[3]))
