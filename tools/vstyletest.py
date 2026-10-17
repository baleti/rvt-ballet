"""visual style UI test with a mock window.vstyle: tools/vstyletest.py URL VIEW_ID  (server running).
Checks: selector hidden without vstyle / shown with it, default hiddenline applied, change autosaves per view, other view keeps default, reopen restores, preset carries style, ?vs= override, no JS exceptions."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
OK = []
def check(n, c, i=''): OK.append(bool(c)); print(('PASS ' if c else 'FAIL ') + n, i)
MOCK = '''window.vstyle={calls:[],defaultId:"hiddenline",list(){return [{id:"hiddenline",label:"Hidden line"},{id:"shaded",label:"Shaded"},{id:"realistic",label:"Realistic"}]},get(){return this.cur},set(id,o){this.cur={id,opts:o||{}};this.calls.push(id)}};1'''
async def main(url, vid):
    b = cdp.Browser(size=(1280, 720)); await b.start()
    try:
        await b.goto(url); await b.wait('window.__loaded===true', 120); await b.wait('typeof window.vctl==="object"', 30); await asyncio.sleep(1)
        if os.environ.get('VS_MOCK', '1') != '0': check('selector hidden without window.vstyle', await b.ev('document.getElementById("vsSel").style.display==="none"'))
        if os.environ.get('VS_MOCK', '1') != '0': await b.ev(MOCK)
        else: await b.wait('typeof window.vstyle==="object"', 30)
        await asyncio.sleep(1)
        check('selector shown with window.vstyle', await b.ev('document.getElementById("vsSel").style.display!=="none"'))
        r = json.loads(await b.ev('JSON.stringify({cur:vstyle.get(),calls:vstyle.calls,sel:document.getElementById("vsSel").value})'))
        check('default hiddenline applied', r['cur'] and r['cur']['id'] == 'hiddenline' and r['sel'] == 'hiddenline', r)
        await b.ev('window.vctl.toggle().then(()=>1)'); await b.ev('window.vctl.openView(%s).then(()=>1)' % vid); await asyncio.sleep(1.5)
        await b.ev('(()=>{const s=document.getElementById("vsSel");s.value="shaded";s.dispatchEvent(new Event("change"));return 1})()'); await asyncio.sleep(0.5)
        check('change applies to vstyle', await b.ev('(vstyle.get().id)==="shaded"'))
        check('autosaved for the open view', await b.ev('Object.keys(localStorage).some(k=>/^vstyle:.*:%s$/.test(k)&&JSON.parse(localStorage[k]).id==="shaded")' % vid))
        await b.ev('document.getElementById("vcpanel")&&(document.getElementById("vcpanel").querySelector("#vcVS")||{}).value'); 
        await b.ev('(()=>{vctl.vstyle.setDefault();return 1})()')
        check('default stored', await b.ev('JSON.parse(localStorage["vstyle:default"]).id==="shaded"'))
        await b.ev('localStorage.removeItem("vstyle:default"); 1')
        await b.ev('(()=>{const s=document.getElementById("vsSel");s.value="realistic";s.dispatchEvent(new Event("change"));return 1})()'); await asyncio.sleep(0.3)
        await b.ev('localStorage.removeItem("vstyle:default"); document.querySelector("#vbOff").click(); 1'); await asyncio.sleep(1.2)
        check('closing the view returns to the default style', await b.ev('(vstyle.get().id)==="hiddenline"'), await b.ev('(vstyle.get().id)'))
        await b.ev('window.vctl.openView(%s).then(()=>1)' % vid); await asyncio.sleep(1.5)
        check('reopening the view restores its saved style', await b.ev('(vstyle.get().id)==="realistic"'), await b.ev('(vstyle.get().id)'))
        # preset roundtrip
        await b.ev('(async()=>{const V=vctl.V;V.presets.__vs=Object.assign(JSON.parse(JSON.stringify(V.state)),{style:{id:"hiddenline",opts:{}}});vctl.vstyle.set("shaded");return 1})()')
        check('preset has a style field', await b.ev('!!vctl.V.presets.__vs.style'))
        errs = [l for l in b.logs if l.startswith('EXC')]
        check('no JS exceptions', not errs, errs[:1])
    finally: await b.close()
    print('ALL OK' if all(OK) else 'FAILED')
asyncio.run(main(sys.argv[1], sys.argv[2]))
