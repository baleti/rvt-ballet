"""overlay alignment test: tools/vcalign.py URL VIEW_ID  (server running). Places the view's datum (grid) linework with the overlay matrix and measures
its distance to the viewer's own whole-model grid lines (independent source: the reader's grids). Prints per-grid offsets in mm; FAIL when the median > 20 mm."""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(url, vid):
    b = cdp.Browser(size=(1280, 720)); await b.start()
    try:
        await b.goto(url); await b.wait('window.__loaded===true', 120); await b.wait('typeof window.vctl==="object"', 30)
        await b.ev('window.vctl.toggle().then(()=>1)'); await b.ev('(window.vctl.openView(%s),1)' % vid); await b.wait('vctl.V.sc&&vctl.V.sc.view.id==%s&&vctl.V.B' % vid, 300); await asyncio.sleep(3)      # big models: the scene takes longer than one evaluate call may wait
        r = json.loads(await b.ev('''(()=>{const V=vctl.V,B=V.B,sc=V.sc,M=V.base; const S=window.S;
          const nat=[]; S.gridGroup.children.forEach(o=>{if(o.isLine){const p=o.geometry.attributes.position;nat.push([new THREE.Vector3(p.getX(0),p.getY(0),p.getZ(0)),new THREE.Vector3(p.getX(1),p.getY(1),p.getZ(1))])}});
          const segs=[]; B.segs.forEach(s=>{const m=B.meta[s.p]; if(m.layer==='datum'){const a=new THREE.Vector3(s.a[0],s.a[1],0).applyMatrix4(M),c=new THREE.Vector3(s.b[0],s.b[1],0).applyMatrix4(M); segs.push([a,c,sc.prims[s.p].elem])}});
          const D=sc.view.dir, DL=Math.hypot(D[0],D[1]), vert=[]; const seen=new Set(); segs.forEach(([p,q,e])=>{if(Math.hypot(q.x-p.x,q.z-p.z)<1e-3&&Math.abs(q.y-p.y)>1e-3&&!seen.has(e)&&(sc.elements[e]||{}).cls==='Grid'){seen.add(e);vert.push(p)}});
          if(vert.length){const off=vert.map(p=>{let best=1e9;nat.forEach(([a,c])=>{const dx=c.x-a.x,dz=c.z-a.z,L=Math.hypot(dx,dz);if(L<1e-6)return;if(DL<1e-6||Math.abs((dx*(-D[1])-dz*D[0])/(L*DL))>0.01)return;const d=Math.abs(((p.x-a.x)*dz-(p.z-a.z)*dx)/L);if(d<best)best=d});return best<1e9?best:null});
            return JSON.stringify({nNat:vert.length,nSeg:segs.length,off,section:1})}
          const out=[]; nat.forEach(([a,c])=>{const dx=c.x-a.x,dz=c.z-a.z,L=Math.hypot(dx,dz); if(L<1e-6)return; let best=null;
            segs.forEach(([p,q])=>{const ex=q.x-p.x,ez=q.z-p.z,l=Math.hypot(ex,ez); if(l<1e-6||Math.abs((dx*ez-dz*ex)/(L*l))>0.01)return;      // parallel only
              const d=Math.abs(((p.x-a.x)*dz-(p.z-a.z)*dx)/L), t=((p.x-a.x)*dx+(p.z-a.z)*dz)/(L*L); if(t<-0.5||t>1.5)return; if(!best||d<best)best=d});
            out.push(best);});
          return JSON.stringify({nNat:nat.length,nSeg:segs.length,off:out})})()'''))
        n = [x for x in r['off'] if x is not None]; mm = sorted(x * 1000 for x in n)
        print('grids', r['nNat'], 'matched', len(n), 'datum segs', r['nSeg'], 'offsets mm (sorted):', [round(x, 1) for x in mm])
        med = mm[len(mm) // 2] if mm else None
        print(('PASS' if med is not None and med <= 20 and len(n) >= 0.8 * r['nNat'] else 'FAIL') + ' overlay alignment, median offset mm', med)
    finally: await b.close()
asyncio.run(main(sys.argv[1], sys.argv[2]))
