"""features: open plan/section/3D views, section box, URL state round trip, measure snapping, phase/level/category isolation, help overlay, param search + zoom, no console errors"""
import asyncio, sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, out):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-ballet'), 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1500, 900)); await b.start(); ok = True
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name)
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 90); await asyncio.sleep(0.5)
        # views
        views = await b.ev("S.meta.views.map((v,i)=>[i,v.kind,!!v.origin,!!v.cut]).filter(x=>x[2])")
        plan = next((v for v in views if v[1] == 'Plan' and v[3]), None); sec = next((v for v in views if v[1] == 'Section'), None); v3 = next((v for v in views if v[1] == '3d'), None)
        for nm, v in (('plan', plan), ('section', sec), ('3d', v3)):
            if v is None: print('skip view', nm); continue
            await b.ev("openView(S.meta.views[%d])" % v[0]); await asyncio.sleep(0.8)
            chk('open %s view' % nm, await b.ev("!document.querySelector('#viewbar').hidden")); await b.shot('%s-view-%s.png' % (out, nm))
        await b.ev("document.querySelector('#vbOff')&&document.querySelector('#vbOff').click()")
        # section box
        await b.ev("document.querySelector('#bSection').click();document.querySelector('#secMode').value='box';document.querySelector('#secMode').dispatchEvent(new Event('change'));document.querySelector('#bxx1').value=500;document.querySelector('#bxx1').dispatchEvent(new Event('input'))"); await asyncio.sleep(0.5)
        chk('section box planes', await b.ev("__renderer.clippingPlanes.length") == 6); await b.shot(out + '-secbox.png')
        # URL state round trip
        await b.ev("selectEl(%d)" % await b.ev("S.meta.elements.findIndex(e=>e[6]!=='none'&&e[2]==='Walls')")); await asyncio.sleep(0.6); await b.ev("document.querySelector('#bLink').click()"); await asyncio.sleep(0.8)
        url = await b.ev("location.href"); chk('hash holds camera/selection/section', all(k in url for k in ('c=', 's=', 'sec=')))
        cam = await b.ev("JSON.stringify(__camera.position.toArray().map(x=>+x.toFixed(2)))")
        await b.goto(url); await b.wait('window.__loaded===true', 90); await asyncio.sleep(1.0)
        chk('state restored (camera)', await b.ev("JSON.stringify(__camera.position.toArray().map(x=>+x.toFixed(2)))") == cam); chk('state restored (selection)', await b.ev("S.sel.size") == 1); chk('state restored (section box)', await b.ev("__renderer.clippingPlanes.length") == 6)
        await b.ev("document.querySelector('#secOff').click()")
        # isolation
        await b.ev("document.querySelector('#tabs button[data-t=levels]').click()"); await asyncio.sleep(0.3)
        await b.ev("document.querySelector('.li[data-l] .only').click()"); await asyncio.sleep(0.4); chk('level only', await b.ev("S.lvlHidden.size") >= 1)
        await b.ev("document.querySelector('#bShowAll').click()"); await b.ev("document.querySelector('#tabs button[data-t=tree]').click()"); await asyncio.sleep(0.3)
        await b.ev("document.querySelector('#tabbody .node .row .tw:nth-of-type(2)')?.click()")
        await b.ev("(()=>{const r=[...document.querySelectorAll('#tabbody .node > .row')].find(r=>/Walls|Ducts|Floors/.test(r.textContent));[...r.querySelectorAll('.tw')].find(t=>t.textContent==='\\u25ce').click()})()"); await asyncio.sleep(0.4)
        chk('category only', await b.ev("S.catHidden.size") >= 1)
        # help
        await b.ev("document.querySelector('#bShowAll').click()"); await b.key('?'); chk('help overlay', await b.ev("!document.querySelector('#help').hidden")); await b.key('Escape')
        # measure snapping
        pts = await b.ev("""(()=>{const r=document.querySelector('#gl').getBoundingClientRect();const o=[];for(let y=r.top+30;y<r.bottom-30;y+=40)for(let x=r.left+30;x<r.right-30;x+=40){const h=pickAt(x,y);if(h)o.push([x,y,h.id,h.p.x,h.p.y,h.p.z])}return o})()""")
        if pts:
            x, y, i, px, py, pz = pts[len(pts) // 2]
            sn = await b.ev("(()=>{const s=snapTo(%d,new THREE.Vector3(%f,%f,%f),50);return s?[s.kind,s.pt.distanceTo(new THREE.Vector3(%f,%f,%f))]:null})()" % (i, px, py, pz, px, py, pz)); chk('snap finds a vertex/edge near a picked point', sn is not None)
        # parameter search -> select + zoom
        await b.ev("document.querySelector('#qParams').checked=true;document.querySelector('#q').value='1';document.querySelector('#q').dispatchEvent(new Event('input'))"); await asyncio.sleep(1.2)
        n = await b.ev("S.hits.length"); chk('param search results (%d)' % n, n > 0)
        errs = [l for l in b.logs if l.startswith('EXC') or 'rror' in l[:40]]; chk('no console errors', not errs)
        if errs: print('\n'.join(errs[:4]))
    finally: await b.close(); srv.terminate()
    print('ALL OK' if ok else 'SOME FAILED'); sys.exit(0 if ok else 1)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
