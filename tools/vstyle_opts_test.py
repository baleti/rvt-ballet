import asyncio, sys, os, json, subprocess, urllib.request
sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet-hl/tools')); import cdp
async def main():
    f = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_writer_house1.rte'); out = sys.argv[1]; port = 9652
    srv = subprocess.Popen([os.environ['RVT_VIEW'], f, '--no-browser', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    base = 'http://127.0.0.1:%d' % port; b = None
    try:
        cdp.wait_http(base + '/api/models', 600); mid = json.load(urllib.request.urlopen(base + '/api/models'))[0]['id']
        b = cdp.Browser(size=(1100, 700)); await b.start(); await b.goto(base + '/#' + mid); await b.wait('window.__loaded===true', 300); await b.wait('window.__hlReady===true', 300)
        await b.ev("window.__errs=[];addEventListener('error',e=>__errs.push(String(e.message)));0")
        for name, js in [('base', "vstyle.set('hiddenline')"), ('faint', "vstyle.set('hiddenline',{hiddenLines:'faint'})"), ('dashed', "vstyle.set('hiddenline',{hiddenLines:'dashed'})"), ('nosil', "vstyle.set('hiddenline',{hiddenLines:'off',silhouettes:false})"),
                         ('angle5', "vstyle.set('hiddenline',{silhouettes:true,edgeAngle:5})"), ('heavy', "vstyle.set('hiddenline',{edgeAngle:30,lineWeight:2})"), ('face', "vstyle.set('hiddenline',{lineWeight:1,faceColor:'#ffe0a0'})")]:
            await b.ev(js + ';0'); await asyncio.sleep(1)
            if name == 'angle5': await b.wait('window.__hlReady===true', 120)
            await asyncio.sleep(1.5); await b.shot('%s/o_%s.png' % (out, name))
        print(await b.ev('JSON.stringify(__errs)'))
    finally:
        if b: await b.close()
        try: os.killpg(srv.pid, 15)
        except Exception: pass
asyncio.run(main())
