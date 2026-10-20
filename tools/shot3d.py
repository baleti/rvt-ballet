"""viewer screenshot at a given view/camera, for side-by-side comparison with Revit exports.
usage: tools/shot3d.py FILE.rvt VIEW CAMERA OUT.png [--size WxH] [--clean] [--units ft|m] [--fov DEG] [--port N] [--up x,y,z] [--ortho [--vh METRES]]
  VIEW   '3d' (model, free camera), a Revit view id (opens that plan/section/3D view as the viewer does) or a view-name substring
  CAMERA 'ex,ey,ez,tx,ty,tz' eye and target in Revit model coordinates (default feet, Z up; --units m for metres), or '-' to keep the view's own / fit camera
  --clean hides the toolbar and panels (viewport only), --fov sets the vertical field of view
Starts its own server on a free port (cached models open instantly; run under tools/capped.sh, host1 via h1run for big files); never opens a visible window."""
import asyncio, sys, os, json, subprocess, argparse, urllib.request
sys.path.insert(0, os.path.dirname(__file__)); import cdp
D = os.path.dirname(os.path.abspath(__file__)) + '/..'
async def main(a):
    port = a.port or (9400 + os.getpid() % 500)
    srv = subprocess.Popen([os.environ.get('RVT_VIEW') or D + '/bin/rvt-view', a.file, '--no-browser', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
    base = 'http://127.0.0.1:%d' % port; b = None
    try:
        cdp.wait_http(base + '/api/models', 600)
        models = json.load(urllib.request.urlopen(base + '/api/models')); mid = [m for m in models if m['name'] == os.path.basename(a.file)][0]['id']
        import time; t = time.time()
        def phase():
            try: return json.load(urllib.request.urlopen('%s/m/%s/meta.json' % (base, mid))).get('phase')
            except Exception: return None      # 404 while the converter has not written the first meta yet
        while phase() != 'done':
            if time.time() - t > 1800: raise SystemExit('model not complete')
            time.sleep(2)
        if a.spec and json.load(open(a.spec)).get('size'): sz = json.load(open(a.spec))['size']; a.size = sz if isinstance(sz, str) else '%dx%d' % tuple(sz)
        if a.style == 'auto' or a.sky_top == 'auto':      # the view's own stored display options (meta views[].display)
            try:
                disp = next((v.get('display') for v in json.load(urllib.request.urlopen('%s/m/%s/meta.json' % (base, mid)))['views'] if str(v['id']) == str(a.view) or v['name'] == a.view), None) or {}
            except Exception: disp = {}
            if a.style == 'auto': a.style = {'hiddenline': 'hidden', 'wireframe': 'wire', 'consistent': 'consistent'}.get(disp.get('vstyle'), 'realistic')
            if a.sky_top == 'auto':
                sk = disp.get('sky') or [180, 205, 220]; a.sky_top = '#%02x%02x%02x' % tuple(sk); a.sky_bottom = '#%02x%02x%02x' % tuple(int(c + (255 - c) * .45) for c in sk)
        if a.like:
            import struct; hd = open(a.like, 'rb').read(24); a.size = '%dx%d' % struct.unpack('>II', hd[16:24])
        w, h = map(int, a.size.split('x')); b = cdp.Browser(size=(w, h)); b.size = (w, h); await b.start()
        await b.goto(base + '/#' + mid); await b.wait('window.__loaded===true', 300); await asyncio.sleep(1)
        if a.spec:
            sp = json.load(open(a.spec)); a.view = a.view if a.view != '3d' else '3d'; k = 0.3048; e = sp['eye']; d = sp['dir']
            a.camera = '%s,%s,%s,%s,%s,%s' % (e[0], e[1], e[2], e[0] - d[0], e[1] - d[1], e[2] - d[2]); a.units = 'ft'
            a.proj = [sp['tl'], sp['tr'], sp['tt'], sp['tb']] if 'tl' in sp else None
        if a.tan:
            import math; a.fov = 2 * math.degrees(math.atan(float(a.tan.split(',')[1])))
        if not hasattr(a, 'proj'): a.proj = None
        if a.clean: await b.ev("(()=>{const s=document.createElement('style');s.textContent='header,#side,#tabs,#panel,#inspector,#help,#status,#viewcube,#viewbar,#banner,#stale,.panel,#left,#right,#vcube,#vhome,.lbl{display:none!important}#view{position:fixed!important;inset:0!important;height:100vh!important}';document.head.appendChild(s);return 0})()")
        await b.ev("window.dispatchEvent(new Event('resize'));0"); await asyncio.sleep(2)      # canvas takes the new size before the view framing is computed
        if a.view != '3d':
            js = "(async()=>{const q=%s;const V=(await (await fetch('/m/%s/meta.json')).json()).views||[];const v=V.find(x=>String(x.id)===q)||V.find(x=>(x.name||'').toLowerCase().includes(q.toLowerCase()));if(!v)return 'no such view (using model camera)';window.openView(v);return 'opened '+v.name})()" % (json.dumps(a.view), mid)
            print(await b.ev(js)); await asyncio.sleep(2)
        if a.camera != '-':
            v = [float(x) for x in a.camera.split(',')]; k = 0.3048 if a.units == 'ft' else 1.0
            r3 = lambda q: [q[0] * k, q[2] * k, -q[1] * k]      # revit (x, y, z up) -> three (x, z, -y)
            e = r3(v[0:3]); t = r3(v[3:6]); up = [float(x) for x in a.up.split(',')] if a.up else [0, 0, 1]; up = [up[0], up[2], -up[1]]
            await b.ev("""(()=>{const e=new THREE.Vector3(%s),t=new THREE.Vector3(%s),up=new THREE.Vector3(%s).normalize(),c=__camera,o=__controls;
              const dir=t.clone().sub(e).normalize();
              if(%s){const m=o.target.clone();const d=m.clone().sub(e).dot(dir);const ctr=e.clone().addScaledVector(dir,d);const H=%s||(c.position.distanceTo(o.target)*2*Math.tan(c.fov*Math.PI/360));
                const fov=2;const D=H/2/Math.tan(fov*Math.PI/360);c.fov=fov;o.target.copy(ctr);c.position.copy(ctr).addScaledVector(dir,-D);c.near=D/50;c.far=D*3+H*50;}
              else{c.position.copy(e);o.target.copy(t);%s}
              c.up.set(0,1,0);c.updateProjectionMatrix();o.update();__dirty();return 0})()""" % (','.join(map(str, e)), ','.join(map(str, t)), ','.join(map(str, up)), 'true' if a.ortho else 'false', a.vh or 0, 'c.fov=%s;' % a.fov if a.fov else ''))
        if a.white or a.hl:
            await b.ev("(()=>{__scene.background=new THREE.Color(0xffffff);__renderer.shadowMap.enabled=false;__scene.traverse(o=>{if(o.material)[].concat(o.material).forEach(m=>m.needsUpdate=true)});if(%s){__overlay.visible=false}else{[...document.querySelectorAll('.lbl')].forEach(e=>e.remove());__overlay.traverse(o=>{if(o.isMesh)o.visible=false})};__dirty();return 0})()" % ('false' if a.levels else 'true'))
        if a.hl:
            await b.ev("""(()=>{const w=__world,add=[];w.traverse(o=>{if(!o.isMesh||o.userData.hl)return;o.userData.hl=1;o.material=new THREE.MeshBasicMaterial({color:0xffffff,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1});
              const l=new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry,30),new THREE.LineBasicMaterial({color:0}));l.userData.hl=1;add.push([o,l])});add.forEach(([o,l])=>o.add(l));__dirty();return 0})()""")
        if a.vg:
            await b.ev("(async()=>{await __hl.loadView({id:%s});return 0})()" % json.dumps(a.vg)); await asyncio.sleep(1)
        a.style = a.style or 'realistic'      # the viewer now opens in hidden line; shots stay shaded unless --style hidden
        if a.style:
            await b.ev("(()=>{__hl.setStyle(%s);return 0})()" % json.dumps(a.style))
            if a.style != 'realistic': await b.wait('window.__hlReady===true', 600); print('edges', await b.ev('__hl.edgeCount+" edges in "+__hl.edgeMs+" ms, meshes "+__hl.meshes.length'))
        if a.fit:
            await b.ev("""(()=>{const c=__camera,o=__controls,B=S.meta.bbox,bb=new THREE.Box3(new THREE.Vector3(B[0][0],B[0][2],-B[1][1]),new THREE.Vector3(B[1][0],B[1][2],-B[0][1]));      // model box from meta (stray far-off meshes must not shrink the view)
              
              const ct=bb.getCenter(new THREE.Vector3()),dir=c.position.clone().sub(o.target).normalize(),pts=[];for(const x of [bb.min.x,bb.max.x])for(const y of [bb.min.y,bb.max.y])for(const z of [bb.min.z,bb.max.z])pts.push(new THREE.Vector3(x,y,z));
              const ndc=(D,tg)=>{c.position.copy(tg).addScaledVector(dir,D);c.near=Math.max(D/2000,0.02);c.far=D*10+500;c.lookAt(tg);c.updateProjectionMatrix();c.updateMatrixWorld(true);let mx=0;for(const p of pts){const q=p.clone().project(c);mx=Math.max(mx,Math.abs(q.x),Math.abs(q.y))}return mx};
              let tg=ct.clone();for(let it=0;it<3;it++){let lo=0.5,hi=1e5;for(let k=0;k<60;k++){const m=Math.sqrt(lo*hi);if(ndc(m,tg)>0.95)lo=m;else hi=m}const D=hi;ndc(D,tg);
                const ctr=new THREE.Vector3();let a=[1e9,-1e9,1e9,-1e9];for(const p of pts){const q=p.clone().project(c);a=[Math.min(a[0],q.x),Math.max(a[1],q.x),Math.min(a[2],q.y),Math.max(a[3],q.y)]}
                const cx=(a[0]+a[1])/2,cy=(a[2]+a[3])/2,right=new THREE.Vector3().setFromMatrixColumn(c.matrixWorld,0),upv=new THREE.Vector3().setFromMatrixColumn(c.matrixWorld,1),hh=D*Math.tan(c.fov*Math.PI/360);
                tg.addScaledVector(right,cx*hh*c.aspect).addScaledVector(upv,cy*hh)}
              let lo=0.5,hi=1e5;for(let k=0;k<60;k++){const m=Math.sqrt(lo*hi);if(ndc(m,tg)>0.95)lo=m;else hi=m}ndc(hi,tg);o.target.copy(tg);o.update();__dirty();return 0})()""")
        print('camera', await b.ev('JSON.stringify([__camera.position.toArray().map(x=>+x.toFixed(2)),__controls.target.toArray().map(x=>+x.toFixed(2)),__camera.fov,__camera.aspect])'))
        if getattr(a, 'proj', None):
            await b.ev("""(()=>{const [tl,tr,tt,tb]=%s,c=__camera;c.fov=2*Math.atan((tt-tb)/2)*180/Math.PI;c.updateProjectionMatrix();c.near=0.05;
              const apply=()=>{const n=c.near;c.projectionMatrix.makePerspective(tl*n,tr*n,tt*n,tb*n,n,c.far);c.projectionMatrixInverse.copy(c.projectionMatrix).invert()};
              c.updateProjectionMatrix=apply;apply();__dirty();return 0})()""" % json.dumps(a.proj))
        if a.sky:
            await b.ev("(()=>{const c=document.createElement('canvas');c.width=2;c.height=256;const g=c.getContext('2d'),gr=g.createLinearGradient(0,0,0,256);gr.addColorStop(0,%s);gr.addColorStop(1,%s);g.fillStyle=gr;g.fillRect(0,0,2,256);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;__scene.background=t;__dirty();return 0})()" % (json.dumps(a.sky_top), json.dumps(a.sky_bottom)))
        if a.edges:
            await b.ev("(()=>{__hl.setStyle('hidden');return 0})()"); await b.wait('window.__hlReady===true', 600)
            await b.ev("(()=>{__hl.setStyle(%s);__hl.group.visible=true;for(const t of __hl.twins)t.visible=false;window.__dirty();return 0})()" % json.dumps(a.style))
            if a.sky: await b.ev("0")
        if a.isolate:      # debug: isolate these Revit element ids (viewer 'rvt-isolate' message)
            await b.ev("(()=>{window.postMessage({type:'rvt-isolate',elementIds:%s},'*');return 0})()" % json.dumps([int(x) for x in a.isolate.split(',')])); await asyncio.sleep(2)
        await asyncio.sleep(3); await b.shot(a.out); print('wrote', a.out)
    finally:
        if b: await b.close()
        try: os.killpg(srv.pid, 15)
        except Exception: pass
p = argparse.ArgumentParser(); p.add_argument('file'); p.add_argument('view'); p.add_argument('camera'); p.add_argument('out')
p.add_argument('--size', default='1280x720'); p.add_argument('--clean', action='store_true'); p.add_argument('--units', default='ft'); p.add_argument('--fov', type=float); p.add_argument('--port', type=int); p.add_argument('--spec', help='JSON perspective camera spec from the sheets reader: {"eye":[x,y,z] ft, "dir":[x,y,z] (Revit ViewDirection, points from target to eye), "tl","tr","tt","tb": crop tangents at unit distance (left right top bottom, e.g. -1 1 1 -1), "size":"WxH"}; overrides VIEW camera/CAMERA/--tan/--size'); p.add_argument('--tan', help='half field-of-view tangents TX,TY of a Revit perspective crop (sets the vertical fov; pass --size with the TX:TY ratio)'); p.add_argument('--edges', action='store_true', help='draw feature/silhouette edges over the realistic or shaded faces'); p.add_argument('--sky-top', default='#b4cddc'); p.add_argument('--sky-bottom', default='#d6e4ea'); p.add_argument('--sky', action='store_true', help='sky gradient background (Revit realistic perspective look)'); p.add_argument('--up'); p.add_argument('--white', action='store_true', help='white background, no level planes / grids / labels / cube'); p.add_argument('--levels', action='store_true', help='with --white: keep levels and grids'); p.add_argument('--hl', action='store_true', help='hidden-line style: white faces, black edges'); p.add_argument('--fit', action='store_true', help='fit the model bounding box into the frame (5%% margin) along the camera direction'); p.add_argument('--like', help='PNG whose pixel size to use'); p.add_argument('--ortho', action='store_true', help='emulate an orthographic camera (narrow fov far away, centred on the view axis through the model centre)'); p.add_argument('--vh', type=float, help='with --ortho: visible height in metres (default: fits the model)'); p.add_argument('--style'); p.add_argument('--isolate', help='debug: comma-separated Revit element ids to isolate before the shot'); p.add_argument('--vg', help='apply the resolved graphics (overrides, filters, hidden elements) of this view id without moving the camera')
asyncio.run(main(p.parse_args()))
