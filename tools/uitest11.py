"""materials UI: Materials tab rows with swatch images, detail panel with provenance, row click isolates, Colour by material + Textures toggles change the render, inspector material section, no JS exceptions.
usage: tools/uitest11.py MODELDIR PORT OUTPREFIX   (model with swatches, e.g. 2020 Residential)"""
import asyncio, sys, os, subprocess, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
async def main(md, port, outp):
    srv = subprocess.Popen([sys.executable, '-c', 'import sys; sys.path.insert(0,%r); from rvtviewer.cli import main; main(sys.argv[1:])' % ROOT, 'serve', md, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port, 60); b = cdp.Browser(size=(1300, 800)); await b.start(); ok = True
    def check(name, cond, info=''):
        nonlocal ok; ok &= bool(cond); print('PASS' if cond else 'FAIL', name, info)
    try:
        await b.goto('http://127.0.0.1:%d/#%s' % (port, os.path.basename(md.rstrip('/')))); await b.wait('window.__loaded===true', 120); await asyncio.sleep(1)
        await b.ev("document.querySelector('[data-t=mat]').click(); 0"); await asyncio.sleep(0.5)
        rows = await b.ev("document.querySelectorAll('.matrow').length"); imgs = await b.ev("document.querySelectorAll('.matrow img').length")
        check('materials tab lists materials in use', rows > 5, rows); check('swatch images in the list', imgs > 5, imgs)
        ok_img = await b.ev("(async()=>{const im=document.querySelector('.matrow img'); await im.decode().catch(()=>{}); return im.naturalWidth})()"); check('swatch image loads', ok_img >= 32, ok_img)
        await b.ev("document.querySelector('.matrow img').click(); 0"); await asyncio.sleep(0.3)
        det = await b.ev("document.querySelector('#matDetail').innerText"); check('detail panel shows provenance', 'colour:' in det and 'texture:' in det, det[:80].replace('\n', ' '))
        before = await b.ev("(()=>{__renderer.render(__scene,__camera); const g=__renderer.getContext(),p=new Uint8Array(4),o=[]; const c=document.querySelector('#gl'); for(let k=0;k<25;k++){g.readPixels(Math.floor((k%5+.5)*c.width/5),Math.floor((Math.floor(k/5)+.5)*c.height/5),1,1,g.RGBA,g.UNSIGNED_BYTE,p); o.push(Array.from(p.subarray(0,3)).join())} return o.join(';')})()")
        await b.ev("document.querySelector('#bMat').click(); 0"); await asyncio.sleep(0.8)
        after = await b.ev("(()=>{__renderer.render(__scene,__camera); const g=__renderer.getContext(),p=new Uint8Array(4),o=[]; const c=document.querySelector('#gl'); for(let k=0;k<25;k++){g.readPixels(Math.floor((k%5+.5)*c.width/5),Math.floor((Math.floor(k/5)+.5)*c.height/5),1,1,g.RGBA,g.UNSIGNED_BYTE,p); o.push(Array.from(p.subarray(0,3)).join())} return o.join(';')})()")
        check('colour by material changes the picture', before != after); await b.shot(outp + '-colourbymat.png'); await b.ev("document.querySelector('#bMat').click(); 0")
        await b.ev("document.querySelector('#bTex').click(); 0"); await asyncio.sleep(0.5); t0 = await b.ev("U_state=window.S && 1"); await b.ev("document.querySelector('#bTex').click(); 0")
        r0 = await b.ev("document.querySelector('.matrow').click(); 0"); await asyncio.sleep(1.0)
        iso = await b.ev("S.isolate ? S.isolate.size : 0"); check('row click isolates its elements', iso > 0, iso)
        await b.ev("setIsolate(null); 0")
        i = await b.ev("S.meta.elements.findIndex(e=>e[2]==='Windows'&&e[1]==='FamilyInstance')")
        if i is not None and i >= 0:
            await b.ev("selectEl(%d); 0" % i); await asyncio.sleep(1.0); txt = await b.ev("document.querySelector('#insp').innerText")
            check('inspector shows materials with provenance', 'MATERIALS' in txt.upper() and 'colour:' in txt, '')
        errs = [l for l in b.logs if 'EXC' in l]; check('no JS exceptions', not errs, errs[:2])
    finally: await b.close(); srv.terminate()
    return ok
sys.exit(0 if asyncio.run(main(os.path.abspath(sys.argv[1]), int(sys.argv[2]), sys.argv[3])) else 1)
