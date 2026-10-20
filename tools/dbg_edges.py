"""debug: open a view in the viewer (hidden line) and report the edge segments of one element: usage tools/dbg_edges.py MODELDIR PORT VIEW_ID ELEMENT_ID [JS_EXTRA [SHOT.png]]"""
import asyncio, sys, os, subprocess, json
sys.path.insert(0, os.path.dirname(__file__)); import cdp
async def main(model_dir, port, vid, eid, js_extra=None, shot=None):
    srv = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rvt-viewer'), 'serve', model_dir, '--port', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cdp.wait_http('http://127.0.0.1:%d/api/models' % port); b = cdp.Browser(size=(1280, 720)); await b.start()
    try:
        await b.goto('http://127.0.0.1:%d/' % port); await b.wait('window.__loaded===true', 240); await asyncio.sleep(1)
        await b.ev("(()=>{__hl.setStyle('hidden');return 0})()"); await b.wait('window.__hlReady===true', 600)
        js = """(()=>{const v=S.meta.views.find(x=>String(x.id)==%s); if(!v) return 'noview'; if(%s) openView(v); return 'ok'})()"""
        print('open', await b.ev(js % (json.dumps(vid), 'true' if vid != '3d' else 'false'))); await asyncio.sleep(8)
        await b.wait('window.__hlReady===true', 600)
        r = await b.ev("""(()=>{const i=S.meta.elements.findIndex(e=>String(e[0])===%s); const out={i, cat:S.meta.elements[i]&&S.meta.elements[i][2], hidden:S.hidden[i], style:__hl.style, kinds:{}, vis:0, tot:0, cam:[__camera.near,__camera.far,__camera.fov]};
          const kinds={}; let hid=0;
          __hl.group.traverse(o=>{ if(!o.isLineSegments||o.userData.ghost) return; const g=o.geometry, e=g.attributes._eidx, k=g.attributes.kind; if(!e) return; for(let s=0;s<e.count;s++) if(Math.round(e.getX(s))===i){ out.tot++; kinds[k.getX(s)]=(kinds[k.getX(s)]||0)+1; } });
          out.kinds=kinds; out.groupVisible=__hl.group.visible; return JSON.stringify(out)})()""" % json.dumps(eid))
        print(r)
        if js_extra: print('extra', await b.ev(js_extra)); await asyncio.sleep(4)
        if shot: await b.shot(shot); print('shot', shot)
    finally: await b.close(); srv.terminate()
asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], *(sys.argv[5:7])))
