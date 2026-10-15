"""attach to an already running (app-mode) Chromium with --remote-debugging-port and run a few real-GPU measurements"""
import asyncio, sys, os, json, urllib.request, aiohttp
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(port, out):
    b = cdp.Browser(); b.port = port; b.id = 0; b.logs = []; b.waiters = {}
    tabs = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % port)); page = [t for t in tabs if t['type'] == 'page'][0]
    b.sess = aiohttp.ClientSession(); b.ws = await b.sess.ws_connect(page['webSocketDebuggerUrl'], max_msg_size=0); b._rd = asyncio.create_task(b._reader())
    await b.call('Runtime.enable')
    print('renderer:', await b.ev("(()=>{const c=document.createElement('canvas').getContext('webgl2');const e=c.getExtension('WEBGL_debug_renderer_info');return c.getParameter(e.UNMASKED_RENDERER_WEBGL)})()"))
    print('status:', await b.ev("document.querySelector('#status').textContent"))
    print('size:', await b.ev("innerWidth+'x'+innerHeight"))
    pk = await b.ev("(()=>{const t0=performance.now();for(let k=0;k<20;k++)pickAt(700+k*3,500);return (performance.now()-t0)/20})()"); print('ms per GPU pick:', round(pk, 1))
    rt = await b.ev("(()=>{const r=window.__renderer,gl=r.getContext();const t0=performance.now();for(let k=0;k<10;k++){r.render(window.__scene,window.__camera)}gl.finish();return (performance.now()-t0)/10})()"); print('ms per full render (GPU, finish-synced):', round(rt, 1))
    await b.shot(out)
    await b.sess.close()
asyncio.run(main(int(sys.argv[1]), sys.argv[2]))
