"""interaction test: scan for a pickable point, real mouse click, check inspector, search, category toggle, section, fidelity colours, measure"""
import asyncio, sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, out):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-viewer'), 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(port=9444); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port); 
        try: await b.wait('window.__loaded===true', 60)
        except TimeoutError: print('LOAD TIMEOUT'); print('\n'.join(b.logs[-10:])); return
        await asyncio.sleep(0.5)
        pts = await b.ev("""(()=>{const r=document.querySelector('#gl').getBoundingClientRect();const out=[];for(let y=r.top+20;y<r.bottom-20;y+=45)for(let x=r.left+20;x<r.right-20;x+=45){const h=pickAt(x,y);if(h)out.push([x,y,h.id])}return out})()""")
        print('pickable grid points:', len(pts))
        x, y, idx = pts[len(pts) // 2]
        await b.click(x, y); await asyncio.sleep(1.0)
        txt = await b.ev("document.querySelector('#insp').innerText.slice(0,500)"); print('--- inspector after real click on element', idx, '\n', txt)
        await b.shot(out + '-select.png')
        await b.ev("document.querySelector('#q').value='duct';document.querySelector('#q').dispatchEvent(new Event('input'))"); await asyncio.sleep(1)
        print('search hits:', await b.ev("S.hits.length"), 'tab', await b.ev("S.tab"))
        await b.ev("document.querySelector('#bFid').click()"); await asyncio.sleep(0.5); await b.shot(out + '-fid.png'); await b.ev("document.querySelector('#bFid').click()")
        await b.ev("setSection('Y', (S.meta.bbox[0][2]+S.meta.bbox[1][2])/2)"); await asyncio.sleep(0.5); await b.shot(out + '-section.png')
        # category toggle through the real tree checkbox, isolate, hide, measure
        await b.ev("document.querySelectorAll('#tabs button')[0].click()")
        r = await b.ev("(()=>{const cb=[...document.querySelectorAll('#tabbody .node > .row')].find(r=>r.textContent.includes('Ducts'));const i=cb.querySelector('input');i.click();return [i.checked, [...S.catHidden].includes('Ducts')]})()")
        print('toggle Ducts via tree checkbox ->', r); await asyncio.sleep(0.4); await b.shot(out + '-nodux.png')
        await b.ev("document.querySelector('#bShowAll').click()")
        for t in ('levels', 'views', 'rooms', 'cov'):
            await b.ev("document.querySelector('#tabs button[data-t=%s]').click()" % t); await asyncio.sleep(0.3)
            print('tab', t, '->', (await b.ev("document.querySelector('#tabbody').innerText.slice(0,160)")).replace('\n', ' | '))
        await b.ev("document.querySelector('#bMeasure').click()")
        await b.click(x, y); await asyncio.sleep(0.3); await b.click(x + 120, y + 40); await asyncio.sleep(0.5)
        print('measure ->', await b.ev("document.querySelector('#status').textContent")); await b.shot(out + '-measure.png')
        print('\n'.join(b.logs[-8:]))
    finally:
        await b.close(); srv.terminate()
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
