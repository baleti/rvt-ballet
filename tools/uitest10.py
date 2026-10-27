"""end-to-end demo check of `rvt-ballet open FILE [--sheets]`: banner while parsing, 3D loads, Sheets button opens the embedded sheets page (iframe), Model button returns; timings.
usage: tools/uitest10.py FILE.rvt [--sheets] [--port N]    (headless Chromium; screenshots in screenshots/demo/)"""
import asyncio, sys, os, subprocess, json, time
sys.path.insert(0, os.path.dirname(__file__)); import cdp
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
async def main(f, sheets, port):
    out = os.path.join(ROOT, 'screenshots', 'demo'); os.makedirs(out, exist_ok=True); tag = os.path.splitext(os.path.basename(f))[0][:30]; ok = True; T = {}
    cmd = [os.path.join(ROOT, 'bin', 'rvt-view'), f, '--no-browser', '--port', str(port)] + (['--sheets'] if sheets else [])
    t0 = time.time(); srv = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port, 60); b = cdp.Browser(size=(1500, 950)); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/%s' % (port, '?sheets=1' if sheets else '')); seen_banner = False; loaded = None
        while time.time() - t0 < 1500:
            await asyncio.sleep(1.5)
            st = json.loads(await b.ev("JSON.stringify({bar: document.querySelector('#parsebar').hidden ? '' : document.querySelector('#parsebar').innerText, phase: window.S && S.meta ? S.meta.phase : null, loaded: window.__loaded===true})"))
            if 'STILL PARSING' in st['bar']: seen_banner = True
            if st['loaded'] and loaded is None: loaded = time.time() - t0; T['first usable (box preview or cache)'] = round(loaded, 1); await b.shot(os.path.join(out, tag + '-1-loaded.png'))
            if st.get('phase') == 'done' and st['loaded']: T['complete'] = round(time.time() - t0, 1); break
        print('PASS' if seen_banner or T.get('complete', 99) < 3 else 'WARN', 'banner shown while parsing (or cache hit)', T)
        # sheets
        btn = await b.ev("[...document.querySelectorAll('#top .plug')].map(x => x.textContent).join('|')"); print('buttons:', btn)
        ok &= 'Sheets' in btn and 'unavailable' not in btn
        t1 = time.time()
        if not sheets: await b.ev("[...document.querySelectorAll('#top .plug')].find(x => x.textContent === 'Sheets').click(); 0")
        await asyncio.sleep(1.0); vis = await b.ev("!document.querySelector('#sheetspane').hidden"); print('PASS' if vis else 'FAIL', 'sheets pane visible', await b.ev("document.querySelector('#shInfo').innerText")); ok &= bool(vis)
        for _ in range(240):
            await asyncio.sleep(1.0)
            n = await b.ev("(()=>{try{const d=document.querySelector('#shFrame').contentDocument; if(!d||!d.body) return '0:0:'; const t=d.body.innerText; return t.length + ':' + d.querySelectorAll('svg,img,canvas').length + ':' + (/reading the \\.rvt|loading|decoding/i.test(t) ? 'busy' : 'ready')}catch(e){return 'x'}})()")
            if n and str(n).endswith(':ready') and int(str(n).split(':')[0]) > 60: break
        T['sheets page ready'] = round(time.time() - t1, 1); print('sheets frame content:', n, T['sheets page ready'], 's'); await b.shot(os.path.join(out, tag + '-2-sheets.png'))
        await b.ev("document.querySelector('#shModel').click(); 0"); await asyncio.sleep(0.5); back = await b.ev("document.querySelector('#sheetspane').hidden"); print('PASS' if back else 'FAIL', 'Model button returns to 3D'); ok &= bool(back)
        errs = [l for l in b.logs if 'EXC' in l]; print('PASS' if not errs else 'FAIL', 'no JS exceptions', errs[:2]); ok &= not errs
        print('TIMINGS', json.dumps(T))
    finally: await b.close(); srv.terminate()
    return ok
if __name__ == '__main__':
    a = sys.argv[1:]; port = int(a[a.index('--port') + 1]) if '--port' in a else 8990
    sys.exit(0 if asyncio.run(main(os.path.abspath(a[0]), '--sheets' in a, port)) else 1)
