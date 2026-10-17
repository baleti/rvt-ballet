"""Revit-style navigation: middle-drag pans, Shift+middle-drag orbits, wheel zooms, left drag does not move the camera (selection only)"""
import asyncio, sys, os, subprocess, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(d, port):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-viewer'), 'serve', d, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1300, 800)); await b.start(); ok = True
    st = "JSON.stringify([...__camera.position.toArray(),...__controls.target.toArray()].map(x=>+x.toFixed(3)))"
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(0.5)
        await b.ev('__controls.enableDamping=false')
        async def delta(fn):
            await asyncio.sleep(1.5); a = json.loads(await b.ev(st)); await fn(); await asyncio.sleep(0.2); c = json.loads(await b.ev(st)); return a, c
        a, c = await delta(lambda: b.drag(700, 400, 760, 440, button='middle')); pan = a[3:] != c[3:] and abs(sum(x - y for x, y in zip(a[:3], c[:3]))) > 0
        print('PASS' if pan else 'FAIL', 'middle-drag pans (target moves)'); ok &= pan
        a, c = await delta(lambda: b.drag(700, 400, 760, 440, button='middle', mods=8)); orb = a[3:] == c[3:] and a[:3] != c[:3]
        print('PASS' if orb else 'FAIL', 'Shift+middle-drag orbits (target fixed, camera moves)', a, c); ok &= orb
        a, c = await delta(lambda: b.drag(700, 400, 760, 440, button='left')); still = a == c
        print('PASS' if still else 'FAIL', 'left-drag leaves the camera alone in Revit mode', a, c); ok &= still
        a, c = await delta(lambda: b.wheel(700, 400, -300)); zoom = a[:3] != c[:3]
        print('PASS' if zoom else 'FAIL', 'wheel zooms'); ok &= zoom
        await b.ev("setNav('orbit')"); a, c = await delta(lambda: b.drag(700, 400, 760, 440, button='left')); orb2 = a[:3] != c[:3]
        print('PASS' if orb2 else 'FAIL', 'Orbit mode: left-drag orbits'); ok &= orb2
        # ViewCube: click the centre of the cube -> the camera looks along a face axis
        box = await b.ev("(()=>{const r=document.querySelector('#vcube').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()")
        await b.click(box[0], box[1]); await asyncio.sleep(0.5)
        d = json.loads(await b.ev("JSON.stringify(__camera.position.clone().sub(__controls.target).normalize().toArray())")); axial = sorted(abs(x) for x in d)[1] < 0.2
        print('PASS' if axial else 'FAIL', 'ViewCube click looks along a face axis', d); ok &= axial
    finally: await b.close(); srv.terminate()
    print('ALL OK' if ok else 'SOME FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1], int(sys.argv[2])))
