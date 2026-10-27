"""progressive first open: start a fresh conversion (no geometry cache) of FILE, watch the page: STILL PARSING banner + watermark + ghost boxes + partial meshes appearing, then the completed model.
usage: tools/uitest8.py FILE.rvt   (headless Chromium; screenshots in screenshots/progress/; timings printed)"""
import asyncio, sys, os, subprocess, json, time
sys.path.insert(0, os.path.dirname(__file__)); import cdp
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
async def main(f, port):
    out = os.path.join(ROOT, 'screenshots', 'progress'); os.makedirs(out, exist_ok=True)
    env = dict(os.environ, RVT_NO_GEOM_CACHE='1', RVT_PARTIAL_SECS=os.environ.get('RVT_PARTIAL_SECS', '4'))
    srv = subprocess.Popen([os.path.join(ROOT, 'rvt-ballet'), 'open', f, '--rebuild', '--no-browser', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port, 60); b = cdp.Browser(size=(1400, 900)); await b.start(); t0 = time.time(); ok = True; seen = []; shots = 0
    try:
        await b.goto('http://127.0.0.1:%d/' % port)
        last = None
        while time.time() - t0 < float(os.environ.get('UITEST_MAX', '900')):
            await asyncio.sleep(2.0)
            st = json.loads(await b.ev("JSON.stringify({bar: document.querySelector('#parsebar').hidden ? '' : document.querySelector('#parsebar').innerText, wm: document.querySelector('#watermark').hidden ? '' : document.querySelector('#watermark').innerText, status: document.querySelector('#status').innerText, loaded: window.__loaded===true, pending: window.S && S.meta ? S.meta.pending : null, phase: window.S && S.meta ? S.meta.phase : null, panel: document.querySelector('#progress').hidden ? '' : document.querySelector('#progress').innerText.slice(0, 60)})"))
            key = (st['bar'][:60], st['wm'][:40], st.get('pending'), st.get('phase'))
            if key != last:
                seen.append((round(time.time() - t0), st)); last = key; print(round(time.time() - t0), 's', json.dumps(st)[:300], flush=True)
                if shots < 8 and (st.get('phase') or st.get('panel')): await b.shot(os.path.join(out, 'step%d.png' % shots)); shots += 1
            if st.get('phase') == 'done' and st['loaded'] and 'Model complete' in st['bar'] + st['status'] + ' Model complete' and not st['wm']: break
        saw_banner = any('STILL PARSING' in s['bar'] for _, s in seen); saw_wm = any('PARTIAL MODEL' in s['wm'] for _, s in seen); saw_partial = len({s.get('pending') for _, s in seen if s.get('pending') is not None}) >= 2
        fin = seen[-1][1]; done = fin.get('phase') == 'done'
        for name, c in (('STILL PARSING banner seen', saw_banner), ('PARTIAL MODEL watermark seen', saw_wm), ('partial refresh (pending count changed)', saw_partial), ('final model loaded', done)):
            print('PASS' if c else 'FAIL', name); ok &= c
        print('total %.0f s' % (time.time() - t0)); print('console:', [l for l in b.logs if 'EXC' in l or 'rror' in l][:8])
    finally: await b.close(); srv.terminate()
    return ok
if __name__ == '__main__':
    sys.exit(0 if asyncio.run(main(os.path.abspath(sys.argv[1]), 8950)) else 1)
