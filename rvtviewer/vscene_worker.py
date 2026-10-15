"""vscene_worker.py FILE.rvt : view-scene worker (run with the rvt-sheets venv, one process per model; rvtviewer/viewctl.py manages it).
Protocol: one JSON request per stdin line, one JSON reply per stdout line.
  {"op": "views"}                                                     -> {"views": [{id, name, kind, scale, template, ...}]}
  {"op": "scene", "view": ID, "scale": N|null, "detail": 1|2|3|null, "template": bool, "filters": bool}  -> scene dict
  {"op": "element", "id": EID}                                        -> {"props": {...}}
Scene = {view: frame/crop/range, prims: [...], elements: {eid: {...}}, options: {...}, stats}. Coordinates: view (u, v) in model feet, frame vectors in world feet."""
import sys, os, json, time
R = os.path.expanduser(os.environ.get('RVTSHEETS', '~/src/rvt-sheets'))
sys.path.insert(0, R)
import numpy as np


def _j(o):
    if hasattr(o, 'tolist'): return o.tolist()
    if isinstance(o, (set, tuple)): return list(o)
    return str(o)


def _round(x, n=4):
    if isinstance(x, float): return round(x, n)
    if isinstance(x, (list, tuple)): return [_round(a, n) for a in x]
    if isinstance(x, np.ndarray): return _round(x.tolist(), n)
    return x


class Worker:
    def __init__(self, path):
        from rvtsheets.drawings import Model
        self.m = Model(path); self.m.start()
        while self.m.state in ('idle', 'loading'): time.sleep(0.3)
        if self.m.state == 'error': raise RuntimeError(self.m.error)
        self.dec, self.doc = self.m.decoder(); self.d = self.m._drawer

    def views(self):
        out = []
        for v in self.doc['views'].values():
            if v.get('template') or not v.get('name') or v.get('error'): continue
            out.append({'id': v['id'], 'name': v['name'], 'kind': v['kind'], 'scale': v.get('scale'), 'template': v.get('view_template'),
                        'detail': v.get('detail_level'), 'drawable': v['kind'] in ('plan', 'section', 'drafting', 'legend', '3d')})
        return {'views': out}

    def scene(self, req):
        vid = int(req['view']); doc = self.doc; d = self.d; vis = d.vis
        v0 = doc['views'][vid]
        saved_scale = v0.get('scale'); eff0 = vis.effective
        opts = {k: req.get(k) for k in ('scale', 'detail', 'template', 'filters')}
        try:
            if req.get('scale'): v0['scale'] = int(req['scale'])
            def eff(v):
                e = dict(eff0(v) if req.get('template', True) is not False else v)
                if req.get('detail'): e['detail_level'] = int(req['detail'])
                if req.get('filters') is False: e['filters'] = None; e['draw_filters'] = None
                return e
            vis.effective = eff
            t0 = time.time(); dr = d.draw(vid)
        finally:
            v0['scale'] = saved_scale; vis.effective = eff0
        info = vis.info.info; cats = doc['categories']; els = {}
        for p in dr['prims']:
            e = p.get('elem')
            if e is None or e in els: continue
            i = info.get(e) or {}; c = i.get('cat'); cc = cats.get(c) or {}
            par = cc.get('parent'); pn = (cats.get(par) or {}).get('name') if par not in (None, -1) else None
            els[e] = {'cls': i.get('cls'), 'cat': c, 'catName': cc.get('name'), 'parent': par if par not in (None, -1) else None, 'parentName': pn}
        keep = ('t', 'elem', 'layer', 'pts', 'segs', 'loops', 'style', 'fill', 'color', 'text', 'origin', 'x', 'size', 'font', 'bold', 'italic', 'halign', 'valign', 'anchor', 'box', 'order', 'cat', 'elems')
        prims = [{k: _round(p[k]) for k in keep if k in p and p[k] is not None} for p in dr['prims'] if p.get('t') != 'image']
        vw = {k: _round(v0.get(k)) for k in ('id', 'name', 'kind', 'scale', 'origin', 'right', 'up', 'dir', 'range', 'discipline', 'detail_level', 'view_template')}
        cr = v0.get('crop') or {}
        vw['crop'] = {k: _round(cr.get(k)) for k in ('origin', 'basis', 'bounds', 'active', 'crop_active', 'annotation_crop_active')} if cr else None
        vw['scale_stored'] = saved_scale; vw['scale'] = int(req['scale']) if req.get('scale') else saved_scale
        try:
            from rvtsheets.compose import crop_rect_uv
            vw['crop_uv'] = _round(crop_rect_uv(v0))
        except Exception: vw['crop_uv'] = None
        return {'view': vw, 'prims': prims, 'elements': {str(k): v for k, v in els.items()}, 'options': opts, 'stats': dr.get('stats'), 'seconds': round(time.time() - t0, 1),
                'key': self.m.key}

    def element(self, req):
        eid = int(req['id']); f = self.dec.f; r = f.rec(eid); i = self.d.vis.info.info.get(eid) or {}
        props = {}
        if r:
            for k, v in (r.get('fields') or {}).items():
                if isinstance(v, (int, float, str, bool)) and not k.startswith('m_n') or isinstance(v, (int, float, str)): props[k] = v
        return {'id': eid, 'cls': i.get('cls'), 'props': props}


def main():
    w = Worker(sys.argv[1])
    out = sys.stdout; sys.stdout = sys.stderr
    print(json.dumps({'ready': True, 'key': w.m.key}, default=_j), file=out, flush=True)
    for line in sys.stdin:
        try:
            req = json.loads(line); op = req.get('op')
            rep = getattr(w, {'views': 'views', 'scene': 'scene', 'element': 'element'}[op])(*([] if op == 'views' else [req]))
        except Exception as ex:
            import traceback; traceback.print_exc(); rep = {'error': '%s: %s' % (type(ex).__name__, ex)}
        print(json.dumps(rep, default=_j, separators=(',', ':')), file=out, flush=True)


if __name__ == '__main__':
    main()
