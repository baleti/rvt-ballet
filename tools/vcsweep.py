"""open every drawable view of a loaded model in the view-control overlay: tools/vcsweep.py URL  (server running). Prints per view: prims, segs, texts, seconds, JS exceptions."""
import asyncio, sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(url):
    b = cdp.Browser(size=(1280, 720)); await b.start(); bad = 0
    try:
        await b.goto(url); await b.wait('window.__loaded===true', 120); await b.wait('typeof window.vctl==="object"', 30)
        await b.ev('window.addEventListener("error",e=>{(window.__errs=window.__errs||[]).push(String(e.message))});window.addEventListener("unhandledrejection",e=>{(window.__errs=window.__errs||[]).push(String(e.reason))});1')
        await b.ev('window.vctl.toggle().then(()=>1)')
        views = json.loads(await b.ev('JSON.stringify(vctl.V.views.filter(v=>v.drawable&&/^(plan|section|drafting|legend)$/.test(v.kind)).map(v=>[v.id,v.name,v.kind]))'))
        for vid, name, kind in views:
            t = time.time()
            try:
                await b.ev('(window.vctl.openView(%s%s),1)' % (vid, ', {model:false}' if os.environ.get('VC_LIGHT') else '')); await b.wait('vctl.V.sc&&vctl.V.sc.view.id==%s&&vctl.V.B' % vid, 300)      # waits outside one evaluate: big views take longer than 30 s
                if os.environ.get('VC_LIGHT'): await b.ev('(vctl.set({model:false}),1)')
                r = json.loads(await b.ev('JSON.stringify({p:vctl.V.sc.prims.length,s:vctl.V.B.segs.length,t:vctl.V.textObjs.length,e:window.__errs||[]})'))
            except Exception as ex: r = {'p': -1, 's': 0, 't': 0, 'e': [str(ex)]}
            ok = not r['e'] and r['p'] >= 0; bad += not ok
            print(('ok  ' if ok else 'FAIL'), vid, kind, name[:30], r['p'], r['s'], r['t'], '%.1fs' % (time.time() - t), r['e'][:2])
    finally: await b.close()
    print('SWEEP', 'OK' if not bad else 'FAIL %d' % bad)
asyncio.run(main(sys.argv[1]))
