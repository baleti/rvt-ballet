"""viewer screenshot at a given view/camera, for side-by-side comparison with Revit exports.
usage: tools/shot3d.py FILE.rvt VIEW CAMERA OUT.png [--size WxH] [--clean] [--units ft|m] [--fov DEG] [--port N] [--up x,y,z] [--ortho [--vh METRES]]
  VIEW   '3d' (model, free camera), a Revit view id (opens that plan/section/3D view as the viewer does) or a view-name substring
  CAMERA 'ex,ey,ez,tx,ty,tz' eye and target in Revit model coordinates (default feet, Z up; --units m for metres), or '-' to keep the view's own / fit camera
  --clean hides the toolbar and panels (viewport only), --fov sets the vertical field of view
Starts its own server on a free port (cached models open instantly; run under tools/capped.sh, remote-host via h1run for big files); never opens a visible window."""
import asyncio, sys, os, json, subprocess, argparse, urllib.request
sys.path.insert(0, os.path.dirname(__file__)); import cdp
D = os.path.dirname(os.path.abspath(__file__)) + '/..'
async def main(a):
    port = a.port or (9400 + os.getpid() % 500)
    srv = subprocess.Popen([D + '/bin/rvt-view', a.file, '--no-browser', '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
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
        w, h = map(int, a.size.split('x')); b = cdp.Browser(size=(w, h)); b.size = (w, h); await b.start()
        await b.goto(base + '/#' + mid); await b.wait('window.__loaded===true', 300); await asyncio.sleep(1)
        if a.clean: await b.ev("(()=>{const s=document.createElement('style');s.textContent='header,#side,#tabs,#panel,#inspector,#help,#status,#viewcube,#viewbar,#banner,.panel,#left,#right{display:none!important}';document.head.appendChild(s);return 0})()")
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
        await asyncio.sleep(3); await b.shot(a.out); print('wrote', a.out)
    finally:
        if b: await b.close()
        try: os.killpg(srv.pid, 15)
        except Exception: pass
p = argparse.ArgumentParser(); p.add_argument('file'); p.add_argument('view'); p.add_argument('camera'); p.add_argument('out')
p.add_argument('--size', default='1280x720'); p.add_argument('--clean', action='store_true'); p.add_argument('--units', default='ft'); p.add_argument('--fov', type=float); p.add_argument('--port', type=int); p.add_argument('--up'); p.add_argument('--ortho', action='store_true', help='emulate an orthographic camera (narrow fov far away, centred on the view axis through the model centre)'); p.add_argument('--vh', type=float, help='with --ortho: visible height in metres (default: fits the model)')
asyncio.run(main(p.parse_args()))
