"""smoke test: serve a converted model, load it headless, check the model loads, picking returns a valid element id, and there are no console errors.
usage: tests/smoke.py MODELDIR [port]   (exit 0 = ok)"""
import asyncio, sys, os, subprocess, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools')); import cdp
async def main(d, port):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rvt-ballet'), 'serve', d, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1200, 800)); await b.start(); bad = []
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 120)
        n = await b.ev('S.N'); tris = await b.ev("document.querySelector('#status').textContent")
        if not n: bad.append('no elements')
        pts = await b.ev("""(()=>{const r=document.querySelector('#gl').getBoundingClientRect();const o=[];for(let y=r.top+r.height*.2;y<r.bottom-r.height*.2;y+=r.height/10)for(let x=r.left+r.width*.2;x<r.right-r.width*.2;x+=r.width/10){const h=pickAt(x,y);if(h)o.push(h.id)}return o})()""")
        if not pts or any(i < 0 or i >= n for i in pts): bad.append('picking returned no / invalid element ids')
        info = json.loads(await b.ev("fetch('/api/m/'+S.mid+'/el/'+%d).then(r=>r.text())" % (pts[0] if pts else 0))) if pts else {}
        if pts and 'el' not in info: bad.append('inspector API failed')
        errs = [l for l in b.logs if l.startswith('EXC') or l.lower().startswith('error')]
        bad += ['console: ' + e[:200] for e in errs]
        print('elements', n, '| picked ids', len(pts), '|', tris)
    finally: await b.close(); srv.terminate()
    print('SMOKE FAIL: ' + '; '.join(bad) if bad else 'SMOKE OK'); sys.exit(1 if bad else 0)
asyncio.run(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8940))
