"""materials UI: textures on/off, colour by material, Materials tab, inspector material section, no JS errors.   usage: tools/uitest9.py MODELDIR   (screenshots in screenshots/materials/)"""
import asyncio, sys, os, subprocess, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
async def main(d, port):
    out = os.path.join(ROOT, 'screenshots', 'materials'); os.makedirs(out, exist_ok=True); ok = True
    srv = subprocess.Popen([os.path.join(ROOT, 'rvt-viewer'), 'serve', d, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1400, 900)); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 120); await asyncio.sleep(0.5)
        await b.ev("fitAll(new THREE.Vector3(1,0.7,1)); 0"); await asyncio.sleep(1.0); await b.shot(os.path.join(out, '1-textures.png'))
        await b.ev("document.querySelector('#bTex').click(); 0"); await asyncio.sleep(0.6); await b.shot(os.path.join(out, '2-no-textures.png')); await b.ev("document.querySelector('#bTex').click(); 0")
        await b.ev("document.querySelector('#bMat').click(); 0"); await asyncio.sleep(0.6); await b.shot(os.path.join(out, '3-colour-by-material.png')); await b.ev("document.querySelector('#bMat').click(); 0")
        await b.ev("document.querySelector('#tabs button[data-t=mat]').click(); 0"); await asyncio.sleep(0.5)
        n = await b.ev("document.querySelectorAll('.matrow').length"); print('PASS' if n else 'FAIL', 'materials tab rows', n); ok &= bool(n)
        await b.shot(os.path.join(out, '4-materials-tab.png'))
        # select an element that has materials
        i = await b.ev("(()=>{const E=S.meta.elements; for (let i=0;i<E.length;i++) if(E[i][6]==='mesh' && !S.meta.defaultHidden.includes(E[i][2])) return i; return -1})()")
        await b.ev("selectEl(%d); 0" % i); await asyncio.sleep(1.2); txt = await b.ev("document.querySelector('#insp').innerText")
        has = 'Materials' in txt or 'texture' in txt; print('PASS' if has else 'WARN', 'inspector shows materials/texture lines'); await b.shot(os.path.join(out, '5-inspector.png'))
        errs = [l for l in b.logs if 'EXC' in l or 'rror' in l]; print('PASS' if not errs else 'FAIL', 'no JS errors', errs[:3]); ok &= not errs
    finally: await b.close(); srv.terminate()
    return ok
if __name__ == '__main__': sys.exit(0 if asyncio.run(main(os.path.abspath(sys.argv[1]), 8960)) else 1)
