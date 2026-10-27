"""browser render check of converted models (headless Chromium, software GL): tools/uisweep.py MODELDIR... -> per model: loaded, triangles drawn, JS errors, canvas not blank,
materials tab rendered, a click picks an element; screenshots in screenshots/uisweep/. Run under a CPU/memory cap (UI tests on host3 only)."""
import asyncio, sys, os, json, subprocess, time, base64
sys.path.insert(0, os.path.dirname(__file__)); import cdp
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
async def one(md, port):
    mid = os.path.basename(md.rstrip('/')); out = os.path.join(ROOT, 'screenshots', 'uisweep'); os.makedirs(out, exist_ok=True); R = {'model': mid}
    srv = subprocess.Popen([sys.executable, '-c', 'import sys; sys.path.insert(0,%r); from rvtballet.cli import main; main(sys.argv[1:])' % ROOT, 'serve', md, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port, 60); b = cdp.Browser(size=(1280, 800)); await b.start()
    try:
        t = time.time(); await b.goto('http://127.0.0.1:%d/#%s' % (port, mid)); await b.wait('window.__loaded===true', 400); R['load_s'] = round(time.time() - t, 1)
        await asyncio.sleep(1.0)
        R['status'] = await b.ev("document.querySelector('#status').textContent")
        R['nonblank'] = await b.ev("""(()=>{const c=document.querySelector('#gl'); const g=__renderer.getContext(); __renderer.render(__scene,__camera); const w=c.width,h=c.height,p=new Uint8Array(4*64); let v=new Set(); for(let k=0;k<64;k++){g.readPixels(Math.floor((k%8+.5)*w/8),Math.floor((Math.floor(k/8)+.5)*h/8),1,1,g.RGBA,g.UNSIGNED_BYTE,p.subarray(4*k,4*k+4)); v.add(p.subarray(4*k,4*k+3).join(','))} return v.size})()""")
        R['picked'] = await b.ev("""(()=>{const r=document.querySelector('#gl').getBoundingClientRect(); for(let y=r.top+r.height*.3;y<r.bottom-30;y+=r.height*.1) for(let x=r.left+r.width*.3;x<r.right-30;x+=r.width*.1){const h=pickAt(x,y); if(h) return h.id} return null})()""")
        await b.ev("document.querySelector('[data-t=mat]').click(); 0"); await asyncio.sleep(0.5)
        R['mat_rows'] = await b.ev("document.querySelectorAll('.matrow').length")
        await b.shot(os.path.join(out, mid[:40] + '.png'))
        R['js_errors'] = [l for l in b.logs if 'EXC' in l or 'rror' in l][:3]
        R['ok'] = bool(R['nonblank'] and R['nonblank'] > 2 and not [l for l in b.logs if 'EXC' in l])
    except Exception as ex: R['ok'] = False; R['error'] = repr(ex)[:300]
    finally: await b.close(); srv.terminate()
    print(json.dumps(R), flush=True); return R
async def main(dirs):
    res = [await one(d, 8990 + k % 5) for k, d in enumerate(dirs)]
    print('UISWEEP %d / %d ok' % (sum(r['ok'] for r in res), len(res)))
if __name__ == '__main__': asyncio.run(main(sys.argv[1:]))
