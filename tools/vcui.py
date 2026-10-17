"""view control UI test with real mouse events: tools/vcui.py URL VIEW_ID  (server running, headless chromium).
Clicks the header 'Annotations' button, opens a view, hovers + clicks a drawn text (tooltip, selection, picked box), clicks 'hide element', checks it hides."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
OK = []
def check(n, c, i=''): OK.append(bool(c)); print(('PASS ' if c else 'FAIL ') + n, i)
async def main(url, vid):
    b = cdp.Browser(size=(1280, 720)); await b.start()
    try:
        await b.goto(url); await b.wait('window.__loaded===true', 120); await b.wait('typeof window.vctl==="object"', 30)
        r = json.loads(await b.ev('(()=>{const r=document.querySelector("#bVC").getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])})()'))
        print('button at', r); await b.click(*r); await b.wait('!!document.querySelector("#vcpanel")', 20)
        check('panel opens on button click', await b.ev('!document.querySelector("#vcpanel").hidden'))
        await b.ev('(()=>{const s=document.querySelector("#vcView");s.value="%s";s.dispatchEvent(new Event("change",{bubbles:true}));return 1})()' % vid)
        await b.wait('vctl.V.sc&&vctl.V.sc.view.id==%s' % vid, 120); await asyncio.sleep(4)
        pt = json.loads(await b.ev('''(()=>{const V=vctl.V,cam=window.__camera,cv=document.querySelector("#gl").getBoundingClientRect(),pr=document.querySelector("#vcpanel").getBoundingClientRect();let best=null;
          V.textObjs.forEach(t=>{if(!t.obj.visible)return;const v=new THREE.Vector3();t.obj.getWorldPosition(v);v.project(cam);if(Math.abs(v.x)>0.9||Math.abs(v.y)>0.9||v.z>1)return;const x=cv.left+(v.x+1)/2*cv.width,y=cv.top+(1-v.y)/2*cv.height;if(x>pr.left-10&&y<pr.bottom+10)return;if(!best||t.pi<best.pi)best={x,y,pi:t.pi}});return JSON.stringify(best)})()'''))
        print(await b.ev('JSON.stringify({n:vctl.V.textObjs.length,vis:vctl.V.textObjs.filter(t=>t.obj.visible).length,cam:__camera.position.toArray().map(x=>Math.round(x))})'))
        check('a text is on screen', pt is not None, pt)
        if pt:
            await b.ev('1'); await b.click(pt['x'], pt['y']); await asyncio.sleep(0.6)
            st = json.loads(await b.ev('JSON.stringify({sel:vctl.V.sel,box:document.querySelector("#vcPicked").innerText.slice(0,80)})'))
            check('click selects the element and fills the picked box', st['sel'] is not None and 'id' in st['box'], st)
            if st['sel'] is not None:
                await b.ev('document.querySelector("#vcHideEl").click()'); await asyncio.sleep(0.4)
                check('hide element hides it', await b.ev('!!vctl.V.state.elems[%s]&&vctl.V.state.elems[%s].vis===false' % (st['sel'], st['sel'])))
        await b.click(5, 5)
        errs = [l for l in b.logs if l.startswith('EXC')]
        check('no JS exceptions', not errs, errs[:1])
    finally: await b.close()
    print('ALL OK' if all(OK) else 'FAILED')
asyncio.run(main(sys.argv[1], sys.argv[2]))
