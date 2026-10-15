"""view control regression test: tools/vctltest.py URL VIEW_ID [OUT.png]  (server already running, model loaded; headless chromium)
Checks: overlay built, text objects, category hide / colour override reach the buffers, annotation-scale re-render halves text, picking, presets, crop uniform."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
OK = []
def check(name, cond, info=''):
    OK.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name, info)
async def main(url, vid, out):
    b = cdp.Browser(size=(1280, 720)); await b.start()
    try:
        await b.goto(url); await b.wait('window.__loaded===true', 120); await b.wait('typeof window.vctl==="object"', 30)
        await b.ev('window.vctl.toggle().then(()=>1)')
        await b.ev('window.vctl.openView(%s).then(()=>1)' % vid); await asyncio.sleep(1)
        st = json.loads(await b.ev('JSON.stringify({prims: vctl.V.sc.prims.length, segs: vctl.V.B.segs.length, texts: vctl.V.textObjs.length, tris: vctl.V.B.tris.length, scale: vctl.V.sc.view.scale, ts: vctl.V.textObjs.length ? vctl.V.sc.prims[vctl.V.textObjs[0].pi].size : 0})'))
        check('overlay built', st['prims'] > 0 and st['segs'] > 0, st)
        check('text objects', st['texts'] > 0)
        # category hide: pick the category with most segments, hide it, its segment widths must be 0 and the others not
        r = json.loads(await b.ev('''(()=>{const V=vctl.V,B=V.B,cnt={};B.segs.forEach(s=>{const c=B.meta[s.p].cat;cnt[c]=(cnt[c]||0)+1});
          const top=Object.entries(cnt).sort((a,b)=>b[1]-a[1])[0][0]; const wA=V.lines.geometry.attributes.aW;
          const live=()=>{let n=0;B.segs.forEach((s,i)=>{if(wA.getX(i*4)>0)n++});return n};
          const before=live(); vctl.V.state.cats[top]={vis:false}; vctl.apply(); const after=live();
          const hid=B.segs.filter((s,i)=>String(B.meta[s.p].cat)===top && wA.getX(i*4)>0).length; vctl.V.state.cats={}; vctl.apply(); return JSON.stringify({top,before,after,hid,restored:live()})})()'''))
        check('category hide', r['after'] < r['before'] and r['hid'] == 0 and r['restored'] == r['before'], r)
        r = json.loads(await b.ev('''(()=>{const V=vctl.V,B=V.B,A=V.lines.geometry.attributes.aCol; const p=B.segs[0].p, cat=B.meta[p].cat; vctl.V.state.cats[String(cat)]={color:'#ff0000'}; vctl.apply();
          const i=B.segs.findIndex(s=>B.meta[s.p].cat===cat); const c=[A.getX(i*4),A.getY(i*4),A.getZ(i*4)]; vctl.V.state.cats={}; vctl.apply(); return JSON.stringify(c)})()'''))
        check('colour override', r[0] > 0.99 and r[1] < 0.01, r)
        r = json.loads(await b.ev('''(()=>{const V=vctl.V; vctl.set({textSize:2}); const s=V.textObjs[0].obj.scale.x; vctl.set({textSize:1}); const on=V.textObjs[0].obj.visible; vctl.set({textOn:false}); const off=V.textObjs[0].obj.visible; vctl.set({textOn:true}); return JSON.stringify({s,on,off})})()'''))
        check('text size / on-off', r['s'] == 2 and r['on'] and not r['off'], r)
        # picking: pick the centre of the first text
        r = json.loads(await b.ev('''(()=>{const V=vctl.V,rc=document.querySelector('#gl').getBoundingClientRect(); let out=null;
          for(const t of V.textObjs){ if(!t.obj.visible) continue; const w=new THREE.Vector3(); t.mesh.getWorldPosition(w); w.project(__camera); if(Math.abs(w.x)>0.9||Math.abs(w.y)>0.9||w.z>1) continue;
            const x=rc.left+(w.x+1)/2*rc.width, y=rc.top+(1-w.y)/2*rc.height; const h=vctl.pick(x,y); out=h?{kind:h.kind,eid:h.eid,cls:h.el.cls,text:h.prim.text,want:V.sc.prims[t.pi].text}:{miss:V.sc.prims[t.pi].text}; if(h&&h.kind==='text') break; }
          return JSON.stringify(out)})()'''))
        check('pick text', r is None or r.get('kind') == 'text', r)       # None: no text on screen in this view
        # annotation scale re-render
        scale0 = st['scale']; new = scale0 // 2 if scale0 % 2 == 0 else scale0 * 2
        await b.ev('(()=>{vctl.V.state.scale=%d; return 1})()' % new)
        await b.ev('fetch("/api/m/"+vctl.V.mid+"/vc/scene/%s?scale=%d").then(r=>r.json()).then(j=>{window.__sc2=j;return 1})' % (vid, new))
        r = json.loads(await b.ev('JSON.stringify({size: __sc2.prims.find(p=>p.t==="text").size, scale: __sc2.view.scale})'))
        check('annotation scale re-render', r['scale'] == new and abs(r['size'] / st['ts'] - new / scale0) < 0.05, (r, st['ts'], new / scale0))
        await b.ev('(()=>{vctl.V.state.scale=null; return 1})()')
        # presets
        await b.ev('fetch("/api/vc/presets",{method:"PUT",body:JSON.stringify({__test:{textSize:3}})}).then(()=>1)')
        r = await b.ev('fetch("/api/vc/presets").then(r=>r.json()).then(j=>JSON.stringify(j))'); check('presets roundtrip', '"__test"' in r, r)
        await b.ev('fetch("/api/vc/presets",{method:"PUT",body:"{}"}).then(()=>1)')
        r = json.loads(await b.ev('(()=>{const had=U_has(); return 1})' if False else 'JSON.stringify({crop: vctl.V.cropUV, on: vctl.V.state.crop})'))
        check('crop data', r['crop'] is None or len(r['crop']) == 4, r)
        if out: await b.shot(out)
        errs = [l for l in b.logs if 'rror' in l and 'favicon' not in l and 'load attempt' not in l]
        check('no console errors', not errs, errs[:3])
    finally: await b.close()
    print('ALL OK' if all(OK) else 'FAILURES'); sys.exit(0 if all(OK) else 1)
asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
