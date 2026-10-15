"""non-blocking first open: start `open` (conversion in background), load the page immediately, record which phases the UI shows (progress card -> box preview -> full model)"""
import asyncio, sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(rvt, port, out):
    srv = subprocess.Popen(['/home/user1/src/rvt-viewer/rvt-viewer', 'open', rvt, '--no-browser', '--rebuild', '--port', str(port)], stdout=open(out + '.srv.log', 'w'), stderr=subprocess.STDOUT)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1300, 800)); await b.start()
    try:
        t0 = time.time(); await b.goto('http://127.0.0.1:%d/' % port); seen = []; shots = 0
        while time.time() - t0 < 90:
            st = await b.ev("JSON.stringify({prog: !document.querySelector('#progress').hidden, ptxt: document.querySelector('#progress').innerText.slice(0,60), status: document.querySelector('#status').textContent, phase: (window.S&&S.meta)?S.meta.phase:null, loaded: window.__loaded===true})")
            d = json.loads(st); key = (d['prog'], d['phase'], d['loaded'])
            if not seen or seen[-1][0] != key:
                seen.append((key, round(time.time() - t0, 1), d['ptxt'] if d['prog'] else d['status'])); shots += 1; await b.shot('%s-%d.png' % (out, shots))
            if d['phase'] == 'done' and d['loaded'] and not d['prog']: break
            await asyncio.sleep(0.4)
        print('logs:', b.logs[-6:])
        for k, t, txt in seen: print('%6.1fs' % t, k, txt.replace('\n', ' | '))
        print('\n'.join(b.logs[-4:]))
    finally: await b.close(); srv.terminate()
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
