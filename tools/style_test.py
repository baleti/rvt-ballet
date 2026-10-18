"""visual style round trip: tools/style_test.py FILE.rvt OUTDIR  -> loads the viewer headless, cycles Hidden Line / Shaded / Consistent / Wireframe / Realistic, one png per style, reports JS errors
(env RVT_VIEW overrides bin/rvt-view; run under tools/capped.sh)"""
import asyncio, sys, os, json, subprocess, urllib.request, time
sys.path.insert(0, os.path.dirname(__file__)); import cdp
D = os.path.dirname(os.path.abspath(__file__)) + '/..'
async def main(f, out):
    os.makedirs(out, exist_ok=True); port = 9400 + os.getpid() % 500
    srv = subprocess.Popen([os.environ.get('RVT_VIEW') or D + '/bin/rvt-view', f, '--no-browser', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    base = 'http://127.0.0.1:%d' % port; b = None; ok = True
    try:
        cdp.wait_http(base + '/api/models', 600)
        mid = [m for m in json.load(urllib.request.urlopen(base + '/api/models')) if m['name'] == os.path.basename(f)][0]['id']
        while json.load(urllib.request.urlopen('%s/m/%s/meta.json' % (base, mid))).get('phase') != 'done': time.sleep(2)
        b = cdp.Browser(size=(1100, 700)); await b.start()
        await b.goto(base + '/#' + mid); await b.wait('window.__loaded===true', 300)
        await b.ev("window.__errs=[];addEventListener('error',e=>__errs.push(String(e.message)));const ce=console.error;console.error=(...a)=>{__errs.push(a.join(' '));ce(...a)};0")
        for st in ['hidden', 'shaded', 'consistent', 'wire', 'realistic', 'hidden']:
            await b.ev("__hl.setStyle(%s);0" % json.dumps(st))
            if st != 'realistic': await b.wait('window.__hlReady===true', 600)
            await asyncio.sleep(1.5); await b.shot('%s/%s.png' % (out, st)); print(st, 'ok', await b.ev("__hl.style+' bg='+__scene.background+' uStyle='+__world.parent.children.length"))
        errs = await b.ev('JSON.stringify(__errs)'); print('js errors:', errs); ok = errs == '[]'
    finally:
        if b: await b.close()
        try: os.killpg(srv.pid, 15)
        except Exception: pass
    print('STYLE-TEST OK' if ok else 'STYLE-TEST FAIL'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1], sys.argv[2]))
