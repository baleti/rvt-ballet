"""parallel / perspective projection of plan, section and elevation views: opening a section view gives the 2 degree telephoto look, the viewbar button switches to perspective (fov 45) and back, closing the view restores fov 45, a 3D view stays perspective; section view depth clips (building section has views[].depth when the model was converted after 2026-10-18).
usage: tools/uitest13.py MODELDIR PORT OUT"""
import asyncio, sys, os, subprocess, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, out):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-viewer'), 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1280, 720)); await b.start(); ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name)
    fov = lambda: b.ev('__camera.fov')
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(1.0)
        chk('model opens in perspective (fov 45)', abs(await fov() - 45) < 1e-6)
        v = await b.ev("(()=>{const m=window.S&&S.meta; if(!m) return 'nometa'; const v=m.views.find(x=>x.kind==='Section'&&x.cut&&x.name==='building section')||m.views.find(x=>x.kind==='Section'&&x.cut); if(!v) return 'noview'; window.openView(v); return v.name})()")
        print('opened', v); await asyncio.sleep(1.5)
        chk('section view opens parallel (fov < 10)', await fov() < 10)
        await b.ev("document.querySelector('#vbProj').click(); 0"); await asyncio.sleep(0.5)
        chk('button switches to perspective (fov 45)', abs(await fov() - 45) < 1e-6)
        await b.ev("document.querySelector('#vbProj').click(); 0"); await asyncio.sleep(0.5)
        chk('button switches back to parallel', await fov() < 10)
        await b.ev("document.querySelector('#vbOff').click(); 0"); await asyncio.sleep(0.5)
        chk('closing the view restores fov 45', abs(await fov() - 45) < 1e-6)
        chk('no console errors', not [l for l in b.logs if 'rror' in l])
    finally: await b.close(); srv.terminate()
    print('ALL OK' if ok else 'SOME FAILED')
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
