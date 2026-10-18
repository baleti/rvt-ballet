import asyncio, sys, os, json, subprocess, urllib.request
sys.path.insert(0, os.path.expanduser('~/src/rvt-viewer-hl/tools')); import cdp
async def main():
    f = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt'); out = sys.argv[1]; port = 9653
    srv = subprocess.Popen([os.environ['RVT_VIEW'], f, '--no-browser', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    base = 'http://127.0.0.1:%d' % port; b = None
    try:
        cdp.wait_http(base + '/api/models', 600); mid = json.load(urllib.request.urlopen(base + '/api/models'))[0]['id']
        b = cdp.Browser(size=(1400, 900)); await b.start(); await b.goto(base + '/#' + mid); await b.wait('window.__loaded===true', 300); await b.wait('window.__hlReady===true', 300)
        print(await b.ev("(async()=>{const V=S.meta.views;const v=V.find(x=>x.id===783882);window.openView(v);return v.name+' '+v.kind})()"))
        await b.wait('__hl.viewReady===true', 60); await asyncio.sleep(2)
        print(await b.ev("JSON.stringify({viewId:__hl.viewId, el:Object.keys(__hl.el||{}).length, hidden:Array.from(S.hidden).reduce((a,x)=>a+x,0)})"))
        await b.shot(out + '/v_open.png')
        await b.ev("document.getElementById('vbOff').click();0"); await asyncio.sleep(2)
        print(await b.ev("JSON.stringify({viewId:__hl.viewId, el:__hl.el?Object.keys(__hl.el).length:null, hidden:Array.from(S.hidden).reduce((a,x)=>a+x,0)})"))
    finally:
        if b: await b.close()
        try: os.killpg(srv.pid, 15)
        except Exception: pass
asyncio.run(main())
