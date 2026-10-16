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
                        'detail': v.get('detail_level'), 'phase': v.get('phase'), 'phaseFilter': v.get('phase_filter'), 'drawable': v['kind'] in ('plan', 'section', 'drafting', 'legend', '3d')})
        ph, pf = self.doc.get('phases') or [], self.doc.get('phase_filters') or []
        return {'views': out, 'phases': [{'id': x['id'], 'name': x['name']} for x in ph], 'phaseFilters': [{'id': x['id'], 'name': x['name']} for x in pf]}

    def scene(self, req):
        vid = int(req['view']); doc = self.doc; d = self.d; vis = d.vis
        v0 = doc['views'][vid]
        saved_scale = v0.get('scale'); eff0 = vis.effective
        opts = {k: req.get(k) for k in ('scale', 'detail', 'template', 'filters', 'cut', 'phase', 'phaseFilter')}
        saved_range = v0.get('range'); saved_phase = (v0.get('phase'), v0.get('phase_filter'))
        try:
            if req.get('scale'): v0['scale'] = int(req['scale'])
            if req.get('cut') is not None and saved_range: v0['range'] = dict(saved_range, cut=float(req['cut']))     # absolute cut plane elevation, feet
            if req.get('phase') is not None: v0['phase'] = int(req['phase'])
            if req.get('phaseFilter') is not None: v0['phase_filter'] = int(req['phaseFilter'])
            def eff(v):
                e = dict(eff0(v) if req.get('template', True) is not False else v)
                if req.get('detail'): e['detail_level'] = int(req['detail'])
                if req.get('filters') is False: e['filters'] = None; e['draw_filters'] = None
                if req.get('phaseFilter') is not None: e['phase_filter'] = int(req['phaseFilter'])
                return e
            vis.effective = eff
            t0 = time.time(); dr = d.draw(vid)
        finally:
            v0['scale'] = saved_scale; vis.effective = eff0; v0['range'] = saved_range; v0['phase'], v0['phase_filter'] = saved_phase
        info = vis.info.info; cats = doc['categories']; els = {}
        for p in dr['prims']:
            e = p.get('elem')
            if e is None or e in els: continue
            i = info.get(e) or {}; c = i.get('cat'); cc = cats.get(c) or {}
            par = cc.get('parent'); pn = (cats.get(par) or {}).get('name') if par not in (None, -1) else None
            els[e] = {'cls': i.get('cls'), 'cat': c, 'catName': cc.get('name'), 'parent': par if par not in (None, -1) else None, 'parentName': pn}
        keep = ('t', 'elem', 'layer', 'pts', 'segs', 'loops', 'style', 'fill', 'color', 'text', 'origin', 'x', 'size', 'font', 'bold', 'italic', 'halign', 'valign', 'anchor', 'box', 'order', 'cat', 'elems', 'part', 'anchor', 'paper', 'gs', 'pattern', 'hang')
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


def warm(path, kinds=('plan', 'section', 'drafting', 'legend')):
    """pre-generate the default scene of every drawable view into the cache (run on host1: tools/vc_warm.sh); prints one line per view"""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from rvtviewer import vcache
    w = Worker(path); n = 0
    for v in w.views()['views']:
        if v['kind'] not in kinds or not v['drawable']: continue
        req = {'op': 'scene', 'view': v['id']}; fn = vcache.cache_fn(path, req)
        if os.path.exists(fn): print('have', v['id'], v['name'], flush=True); continue
        t0 = time.time()
        try: js = json.dumps(w.scene(req), default=_j, separators=(',', ':'))
        except Exception as ex: print('FAIL', v['id'], v['name'], repr(ex)[:120], flush=True); continue
        os.makedirs(vcache.CACHE, exist_ok=True); open(fn + '.tmp', 'w').write(js); os.replace(fn + '.tmp', fn); n += 1
        print('ok', v['id'], v['kind'], v['name'], '%.1fs %dKB' % (time.time() - t0, len(js) // 1024), flush=True)
    print('warmed %d scenes' % n)


def main():
    if len(sys.argv) > 2 and sys.argv[2] == '--warm': return warm(sys.argv[1])
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
