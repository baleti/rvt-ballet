"""second interaction pass: hide / isolate (ghost) / level visibility / fidelity colours / orbit-pan-zoom with real mouse events / tree select / search click"""
import asyncio, sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, out):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-ballet'), 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(0.5)
        cam0 = await b.ev("JSON.stringify(__camera.position.toArray().map(x=>+x.toFixed(2)))")
        await b.drag(700, 500, 820, 450); await asyncio.sleep(0.4); cam1 = await b.ev("JSON.stringify(__camera.position.toArray().map(x=>+x.toFixed(2)))")
        await b.drag(700, 500, 760, 520, button='right'); await asyncio.sleep(0.4); tgt = await b.ev("JSON.stringify(__controls?0:0)")
        await b.wheel(700, 500, -300); await asyncio.sleep(0.4); cam2 = await b.ev("JSON.stringify(__camera.position.toArray().map(x=>+x.toFixed(2)))")
        print('orbit moved camera:', cam0 != cam1, '| wheel zoom moved camera:', cam1 != cam2)
        await b.shot(out + '-nav.png')
        pts = await b.ev("""(()=>{const r=document.querySelector('#gl').getBoundingClientRect();const out=[];for(let y=r.top+20;y<r.bottom-20;y+=40)for(let x=r.left+20;x<r.right-20;x+=40){const h=pickAt(x,y);if(h)out.push([x,y,h.id])}return out})()"""); print('pickable points', len(pts))
        x, y, idx = pts[len(pts) // 3]
        await b.click(x, y); await asyncio.sleep(0.8)
        sel = await b.ev("[...S.sel]"); print('selected via click:', sel == [idx], sel)
        await b.key('h'); await asyncio.sleep(0.5)
        h = await b.ev("S.hidden[%d]" % idx); print('H key hid selection:', h == 1)
        again = await b.ev("(()=>{const h=pickAt(%d,%d);return h?h.id:-1})()" % (x, y)); print('hidden element no longer pickable at same pixel:', again != idx)
        await b.ev("document.querySelector('#bShowAll').click()"); await asyncio.sleep(0.3)
        await b.click(x, y); await asyncio.sleep(0.5); await b.key('i'); await asyncio.sleep(0.6); await b.shot(out + '-isolate.png')
        print('isolate active:', await b.ev("!!S.isolate"))
        await b.key('i'); await b.ev("document.querySelector('#bFid').click()"); await asyncio.sleep(0.5); await b.shot(out + '-fid.png'); await b.ev("document.querySelector('#bFid').click()")
        lv = await b.ev("S.meta.levels.length"); 
        if lv:
            await b.ev("document.querySelector('#tabs button[data-t=levels]').click()"); await asyncio.sleep(0.3)
            await b.ev("document.querySelector('#tabbody .li input').click()"); await asyncio.sleep(0.4)
            print('level visibility toggled:', await b.ev("S.lvlHidden.size"))
            await b.shot(out + '-level.png')
        await b.ev("document.querySelector('#bShowAll').click()")
        await b.ev("document.querySelector('#tabs button[data-t=tree]').click()"); await asyncio.sleep(0.3)
        await b.ev("(()=>{const n=[...document.querySelectorAll('#tabbody .node > .row')].find(r=>/Walls|Ducts|Floors/.test(r.textContent));n.querySelector('.tw').click()})()"); await asyncio.sleep(0.3)
        await b.ev("(()=>{const n=document.querySelector('#tabbody .node .kids .node .row .tw');n&&n.click()})()"); await asyncio.sleep(0.3)
        await b.ev("(()=>{const l=document.querySelector('#tabbody .row[data-i]');l&&l.click()})()"); await asyncio.sleep(0.8)
        print('tree leaf click selected:', await b.ev("S.sel.size"), '| inspector:', (await b.ev("document.querySelector('#insp h2')?.textContent")))
        print('\n'.join(b.logs[-6:]))
    finally:
        await b.close(); srv.terminate()
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
