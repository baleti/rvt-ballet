import asyncio, sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, gl):
    srv = subprocess.Popen(['/home/user1/src/rvt-viewer/rvt-viewer', 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port)
    b = cdp.Browser(gl=gl); await b.start()
    try:
        t = time.time(); await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 180); print('load secs', round(time.time() - t, 1))
        print('status:', await b.ev("document.querySelector('#status').textContent"))
        print('gl renderer:', await b.ev("(()=>{const c=document.createElement('canvas').getContext('webgl2');const e=c.getExtension('WEBGL_debug_renderer_info');return c.getParameter(e.UNMASKED_RENDERER_WEBGL)})()"))
        # measure render time by forcing frames while orbiting
        r = await b.ev("""(async()=>{const t0=performance.now();let n=0;for(let k=0;k<20;k++){window.__rot=(window.__rot||0)+0.05;const c=document.querySelector('#gl');
          const ev=new PointerEvent('pointermove');S.hoverI=-2;window.dispatchEvent(new Event('resize'));await new Promise(r=>requestAnimationFrame(r));n++}return (performance.now()-t0)/n})()""")
        print('ms/frame approx (rAF cadence):', round(r, 1))
        t = time.time(); await b.drag(700, 500, 900, 560); await asyncio.sleep(0.3)
        pk = await b.ev("(()=>{const t0=performance.now();for(let k=0;k<20;k++)pickAt(700+k*3,500);return (performance.now()-t0)/20})()"); print('ms per GPU pick:', round(pk, 1))
        rt = await b.ev("""(()=>{const r=window.__renderer,s=window.__scene,c=window.__camera,g=r.getContext(),px=new Uint8Array(4);const t=(n,f)=>{f&&f();r.render(s,c);g.readPixels(0,0,1,1,g.RGBA,g.UNSIGNED_BYTE,px);const t0=performance.now();for(let k=0;k<n;k++){f&&f();r.render(s,c);g.readPixels(0,0,1,1,g.RGBA,g.UNSIGNED_BYTE,px)}return +((performance.now()-t0)/n).toFixed(1)};
          const plain=t(10), sh=t(5,()=>{r.shadowMap.needsUpdate=true}); document.querySelector('#bSection').click(); const caps=t(10); document.querySelector('#bSection').click(); return JSON.stringify({plain, withShadowUpdate: sh, sectionCaps: caps})})()""")
        print('ms per synced full render:', rt)
        rs = await b.ev("(()=>{const t0=performance.now();for(let k=0;k<5;k++)refreshState();return (performance.now()-t0)/5})()"); print('ms per refreshState (visibility change):', round(rs, 1))
        if os.environ.get('PERF_SHOT'): await b.shot(os.environ['PERF_SHOT'])
    finally:
        await b.close(); srv.terminate()
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'swiftshader'))
