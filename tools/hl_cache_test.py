"""edge cache (IndexedDB) round trip: build edges, change edgeAngle and back, the second build with the first parameters must come from the cache (RVT_VIEW = launcher, see tools/style_test.py)"""
import asyncio, sys, os, json, subprocess, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import cdp
async def main(f):
    port = 9400 + os.getpid() % 500
    srv = subprocess.Popen([os.environ.get('RVT_VIEW') or os.path.dirname(os.path.abspath(__file__)) + '/../bin/rvt-view', f, '--no-browser', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    base = 'http://127.0.0.1:%d' % port; b = None; ok = False
    try:
        cdp.wait_http(base + '/api/models', 600); mid = json.load(urllib.request.urlopen(base + '/api/models'))[0]['id']
        b = cdp.Browser(size=(900, 600)); await b.start(); await b.goto(base + '/#' + mid); await b.wait('window.__loaded===true', 300); await b.wait('window.__hlReady===true', 300)
        t1 = await b.ev('__hl.edgeMs'); n1 = await b.ev('__hl.edgeCount')
        for ang in (31, 30):
            await b.ev('window.__hlReady=false;vstyle.set("hiddenline",{edgeAngle:%d});0' % ang); await b.wait('window.__hlReady===true', 300)
            print('angle', ang, 'edges', await b.ev('__hl.edgeCount'), 'ms', await b.ev('__hl.edgeMs'))
        t3 = await b.ev('__hl.edgeMs'); n3 = await b.ev('__hl.edgeCount'); print('first build %s ms, cached rebuild %s ms' % (t1, t3)); ok = n1 == n3 and t3 <= max(t1, 40)
    finally:
        if b: await b.close()
        try: os.killpg(srv.pid, 15)
        except Exception: pass
    print('HL-CACHE-TEST OK' if ok else 'HL-CACHE-TEST FAIL'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1]))
