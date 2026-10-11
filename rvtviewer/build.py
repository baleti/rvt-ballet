"""rvt -> cache: model.glb (batched by category, per-vertex element index), meta.json (tree, levels, grids, ...), model.sqlite (elements + parameters)."""
import os, sys, json, time, math, sqlite3, hashlib, colorsys, collections
import numpy as np
from . import reader, geom, glb
from .geom import Mesh

FID_ORDER = ['solid', 'param', 'bbox', 'line', 'none']      # honesty ladder shown in the UI
FID_LABEL = {'solid': 'decoded B-rep', 'param': 'rebuilt from stored parameters (approximate: no joins/openings)', 'bbox': 'placeholder at true bounding box', 'line': 'curve', 'none': 'no geometry'}

CAT_COLORS = {
    'Walls': (0.82, 0.80, 0.76), 'Floors': (0.70, 0.66, 0.60), 'Roofs': (0.60, 0.35, 0.30), 'Ceilings': (0.90, 0.90, 0.88),
    'Structural Columns': (0.55, 0.60, 0.68), 'Structural Framing': (0.50, 0.62, 0.78), 'Structural Foundations': (0.55, 0.50, 0.45),
    'Ducts': (0.30, 0.65, 0.85), 'Duct Fittings': (0.25, 0.55, 0.75), 'Flex Ducts': (0.40, 0.72, 0.88), 'Pipes': (0.30, 0.80, 0.45), 'Pipe Fittings': (0.25, 0.65, 0.40),
    'Conduits': (0.85, 0.65, 0.25), 'Cable Trays': (0.90, 0.75, 0.30), 'Doors': (0.62, 0.45, 0.30), 'Windows': (0.55, 0.78, 0.90),
    'Stairs': (0.75, 0.72, 0.65), 'Railings': (0.60, 0.60, 0.62), 'Furniture': (0.78, 0.60, 0.45), 'Plumbing Fixtures': (0.85, 0.88, 0.92),
    'Lighting Fixtures': (0.98, 0.90, 0.50), 'Mechanical Equipment': (0.45, 0.70, 0.55), 'Electrical Equipment': (0.90, 0.55, 0.30),
    'Curtain Panels': (0.60, 0.80, 0.90), 'Curtain Wall Mullions': (0.50, 0.52, 0.55), 'Structural Rebar': (0.75, 0.30, 0.25), 'Topography': (0.55, 0.62, 0.45),
    'Lines': (0.2, 0.2, 0.2),
}
def cat_color(name):
    c = CAT_COLORS.get(name)
    if c: return c
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16) / 0xffffff
    return colorsys.hls_to_rgb(h, 0.62, 0.35)

def g(o, *path, default=None):
    """navigate decoded record fields; transparently steps through pointer slots ('obj')"""
    for p in path:
        if isinstance(o, dict) and 'obj' in o and p not in o: o = o['obj']
        if isinstance(o, dict) and p in o: o = o[p]
        else: return default
    if isinstance(o, dict) and 'obj' in o: o = o['obj']
    return o

class Ctx:
    def __init__(self, raw):
        self.raw = raw; self.W = raw['W']
        self.recs = {}; self.cls_of = {}
        for (e, c), r in raw['recs'].items():
            if e not in self.recs: self.recs[e] = r
        self.eh = raw['eh']; self.par = raw['params']
        self.cat = reader.category_names()
        self.levels = {}      # id -> (name, elev ft)
        for e, r in self.recs.items():
            if r['class'] == 'Level':
                o = g(r['fields'], 'm_pSurface', 'm_origin'); self.levels[e] = (r['fields'].get('m_text') or self.par.get(e, {}).get('params', {}).get('Name') or 'Level %d' % e, o[2] if o else None)
    def sc(self, v):
        v = int(v); b = 8 * self.W
        return v - (1 << b) if v >= 1 << (b - 1) else v
    def catid(self, e):
        h = self.eh.get(e); return self.sc(h['m_categroryId']) if h else None
    def catname(self, e):
        c = self.catid(e)
        if c is None: return None
        return self.cat.get(str(c), 'Category %d' % c) if c != -1 else None
    def bbox(self, e):
        h = self.eh.get(e); bb = g(h, 'm_pBBox', 'm_minmax') if h else None
        if not bb: return None
        lo, hi = np.array(bb[0], float), np.array(bb[1], float)
        if np.any(np.abs(lo) > 1e8) or np.any(np.abs(hi) > 1e8) or np.any(hi < lo): return None
        return lo, hi
    def eid_int(self, v):
        if v is None: return None
        v = self.sc(v); return None if v < 0 else v

# ---------------------------------------------------------------- element table

def type_of(ctx, e, r):
    p = ctx.par.get(e, {}).get('params', {})
    t = ctx.eid_int(r['fields'].get('m_masterSymbolId')) if 'm_masterSymbolId' in r['fields'] else None
    if t is None:
        for k in ('Type Id', 'Type'):
            v = p.get(k)
            if isinstance(v, int) and v != e: t = ctx.eid_int(v); break
    return t if t in ctx.recs else None

def build_table(ctx):
    els = []
    for e, r in ctx.recs.items():
        if e not in ctx.eh and r['class'] not in ('Level', 'Grid'): pass
        p = ctx.par.get(e, {}).get('params', {})
        tid = type_of(ctx, e, r)
        name = p.get('Name') or p.get('Type Name') or r['fields'].get('m_name') or r['fields'].get('m_text') or r['fields'].get('m_viewName')
        tname = None
        if tid is not None:
            tp = ctx.par.get(tid, {}).get('params', {}); tname = tp.get('Type Name') or tp.get('Name') or ctx.recs[tid]['fields'].get('m_name')
        is_type = 'Type Name' in p and tid is None and ctx.eid_int(p.get('Type Id')) in (None, e)
        els.append({'id': e, 'cls': r['class'], 'cat': ctx.catname(e), 'name': name if isinstance(name, str) else None, 'type': tname if isinstance(tname, str) else None,
                    'typeId': tid, 'isType': bool(is_type), 'uid': p.get('UniqueId'), 'ifc': p.get('IfcGUID'), 'fid': 'none', 'bb': ctx.bbox(e)})
    return els

# ---------------------------------------------------------------- geometry builders (return (Mesh, fidelity) in feet)

def plane_of(surf):
    if not isinstance(surf, dict) or 'm_origin' not in surf or 'm_xVec' not in surf or 'm_yVec' not in surf: return None
    o = np.array(surf['m_origin'], float); x = np.array(surf['m_xVec'], float); y = np.array(surf['m_yVec'], float)
    env = surf.get('m_Envelope', {}).get('m_corners') if isinstance(surf.get('m_Envelope'), dict) else None
    return o, x, y, env

def ref_planes(f):
    out = []
    for fc in f.get('m_pRefFaces') or []:
        pl = plane_of(g(fc, 'm_pSurf'))
        if pl: out.append(pl)
    return out

def wall_geom(ctx, e, r):
    pls = ref_planes(r['fields'])
    pls = [p for p in pls if p[3]]
    if not pls: return None
    o0, x0, y0, _ = pls[0]; n = np.cross(x0, y0); nn = np.linalg.norm(n)
    if nn < 1e-9: return None
    n /= nn; x0 = x0 / np.linalg.norm(x0); y0 = y0 / np.linalg.norm(y0)
    ext = np.array([[1e30] * 3, [-1e30] * 3])
    for o, x, y, env in pls:
        (u0, v0), (u1, v1) = env
        for u in (u0, u1):
            for v in (v0, v1):
                q = o + x * u + y * v; c = np.array([np.dot(q - o0, x0), np.dot(q - o0, n), np.dot(q - o0, y0)])
                ext[0] = np.minimum(ext[0], c); ext[1] = np.maximum(ext[1], c)
    if np.any(ext[1] - ext[0] < 1e-6): return None
    d = ext[1] - ext[0]
    return geom.obox(o0 + x0 * ext[0][0] + n * ext[0][1] + y0 * ext[0][2], x0 * d[0], n * d[1], y0 * d[2]), 'param'

def sketch_loops(ctx, e):
    """boundary loops (3D points, feet) of the sketch that belongs to element e (found via ElementHeader parents)"""
    h = ctx.eh.get(e); par = g(h, 'm_parents', 'm_deletion') if h else None
    for pid in par or []:
        pid = int(pid); r = ctx.recs.get(pid)
        if not r or r['class'] not in ('VarSketch', 'Sketch'): continue
        pairs = g(r['fields'], 'm_elemIdsPairSet', 'm_data') or []
        segs = []
        for it in pairs:
            ce = ctx.recs.get(int(it['m_elementId']))
            if not ce: continue
            s = curve_pts(g(ce['fields'], 'm_pCurveDriver', 'm_pCrv'))
            if s is not None: segs.append(s)
        if segs: return geom.chain_loops(segs)
    return None

def curve_pts(c, maxdeg=10):
    if not isinstance(c, dict): return None
    if 'm_dirVec' in c and 'm_endParams' in c and 'm_origin' in c:
        o = np.array(c['m_origin'], float); d = np.array(c['m_dirVec'], float); t0, t1 = c['m_endParams']
        return np.array([o + d * t0, o + d * t1])
    if 'm_radius' in c and 'm_center' in c and 'm_endParams' in c:
        ctr = c['m_center']; R = c['m_radius']; t0, t1 = c['m_endParams']
        nv = c.get('m_normal') or c.get('m_zVec') or [0, 0, 1]; xv = c.get('m_xVec') or c.get('m_refVec') or [1, 0, 0]
        return geom.arc_points(ctr, R, t0, t1, nv, xv, maxdeg)
    return None

def slab_geom(ctx, e, r):
    pls = ref_planes(r['fields'])
    if not pls: return None
    zs = [p[0][2] for p in pls if abs(np.cross(p[1], p[2])[2]) > 0.999]
    if len(zs) < 2: return None
    loops = sketch_loops(ctx, e)
    if not loops: return None
    closed = [l for l in loops if len(l) >= 3]
    if not closed: return None
    areas = [abs(0.5 * np.sum(l[:, 0] * np.roll(l[:, 1], -1) - np.roll(l[:, 0], -1) * l[:, 1])) for l in closed]
    order = np.argsort(areas)[::-1]
    outer = closed[order[0]][:, :2]
    holes = [closed[i][:, :2] for i in order[1:] if areas[i] > 1e-6]
    m = geom.prism([outer] + holes, min(zs), max(zs))
    return (m, 'param') if m else None

BUILDERS = {'SWall': wall_geom, 'Floor': slab_geom}

def element_mesh(ctx, e, r):
    fn = BUILDERS.get(r['class'])
    if fn:
        try:
            res = fn(ctx, e, r)
            if res and res[0]: return res
        except Exception as ex:
            if os.environ.get('RVT_DEBUG'): print('builder', r['class'], e, repr(ex))
    bb = ctx.bbox(e)
    if bb is not None: return geom.box(*bb), 'bbox'
    return None

# ---------------------------------------------------------------- datum / spatial

def build_levels(ctx):
    out = []
    for e, (n, z) in ctx.levels.items():
        if z is not None: out.append({'id': e, 'name': n, 'elev': z * 0.3048})
    return sorted(out, key=lambda l: l['elev'])

def build_grids(ctx):
    out = []
    for e, r in ctx.recs.items():
        if r['class'] != 'Grid': continue
        pts = curve_pts(g(r['fields'], 'm_pCurveDriver', 'm_pCrv')) or curve_pts(g(r['fields'], 'm_pCurve')) 
        if pts is None:
            for k, v in r['fields'].items():
                pts = curve_pts(g(v)) if isinstance(v, dict) else None
                if pts is not None: break
        if pts is None: continue
        out.append({'id': e, 'name': r['fields'].get('m_text', ''), 'pts': [[round(float(a) * 0.3048, 4) for a in p] for p in pts[[0, -1]]]})
    return out

# ---------------------------------------------------------------- main

def convert(path, outdir, log=print):
    t0 = time.time(); os.makedirs(outdir, exist_ok=True)
    raw = reader.cached_load(path, log); ctx = Ctx(raw)
    els = build_table(ctx); log('%d elements' % len(els))
    levels = build_levels(ctx); lvl_by_id = {l['id']: l['name'] for l in levels}
    # level per element
    for el in els:
        r = ctx.recs[el['id']]; p = ctx.par.get(el['id'], {}).get('params', {})
        lv = None
        for k in ('m_assocLevelId', 'm_levelId', 'm_scheduleOnlyLevelId'):
            v = ctx.eid_int(r['fields'].get(k)) if k in r['fields'] else None
            if v in lvl_by_id: lv = v; break
        if lv is None:
            for k in ('Level', 'Base Constraint', 'Schedule Level', 'Base Level', 'Reference Level'):
                v = ctx.eid_int(p.get(k)) if isinstance(p.get(k), int) else None
                if v in lvl_by_id: lv = v; break
        el['level'] = lvl_by_id.get(lv)
    # geometry
    cats = collections.OrderedDict(); acc = {}   # category -> dict(pos list, eidx list, idx list, ranges)
    stats = collections.Counter(); covg = collections.defaultdict(collections.Counter)
    for i, el in enumerate(els):
        el['i'] = i
        r = ctx.recs[el['id']]
        res = element_mesh(ctx, el['id'], r) if (el['cat'] and not el['isType']) else None
        if res is None:
            covg[el['cat'] or '(none)']['none'] += 1; continue
        mesh, fid = res
        el['fid'] = fid; covg[el['cat']][fid] += 1
        a = acc.setdefault(el['cat'], {'pos': [], 'idx': [], 'eidx': [], 'ranges': [], 'nv': 0, 'nt': 0})
        a['pos'].append(mesh.v); a['idx'].append(mesh.f.reshape(-1) + a['nv']); a['eidx'].append(np.full(len(mesh.v), i, np.float32))
        a['ranges'] += [i, a['nt'], len(mesh.f)]; a['nv'] += len(mesh.v); a['nt'] += len(mesh.f)
    batches = []; bmeta = []
    for cat, a in acc.items():
        pos = glb.to_yup_m(np.vstack(a['pos'])); idx = np.concatenate(a['idx']).astype(np.uint32)
        # y-up conversion mirrors z -> flips handedness; winding is unimportant (double sided)
        c = cat_color(cat); alpha = 0.45 if cat in ('Windows', 'Curtain Panels') else 1.0
        batches.append({'name': cat, 'color': (*c, alpha), 'pos': pos, 'eidx': np.concatenate(a['eidx']), 'idx': idx})
        bmeta.append({'cat': cat, 'color': '#%02x%02x%02x' % tuple(int(x * 255) for x in c), 'alpha': alpha, 'ranges': a['ranges'], 'tris': a['nt']})
    glb.write_glb(os.path.join(outdir, 'model.glb'), batches)
    # metadata
    allb = [el['bb'] for el in els if el['bb'] is not None and el['fid'] != 'none']
    if allb:
        lo = np.min([b[0] for b in allb], 0) * 0.3048; hi = np.max([b[1] for b in allb], 0) * 0.3048
    else: lo = hi = np.zeros(3)
    meta = {'file': os.path.basename(path), 'version': None, 'levels': levels, 'grids': build_grids(ctx), 'batches': bmeta,
            'bbox': [lo.tolist(), hi.tolist()], 'fidLabels': FID_LABEL,
            'elements': [[el['id'], el['cls'], el['cat'], el['name'], el['type'], el['level'], el['fid'], el['isType']] for el in els],
            'coverage': {k: dict(v) for k, v in covg.items()}, 'built': time.time(), 'buildSecs': 0}
    # sqlite
    dbp = os.path.join(outdir, 'model.sqlite')
    if os.path.exists(dbp): os.remove(dbp)
    db = sqlite3.connect(dbp)
    db.executescript('create table el(i integer primary key, id integer, cls text, cat text, name text, type text, level text, uid text, ifc text, fid text, bb text);'
                     'create table prm(i integer, k text, v text);create index prm_i on prm(i);')
    db.executemany('insert into el values(?,?,?,?,?,?,?,?,?,?,?)', [(el['i'], el['id'], el['cls'], el['cat'], el['name'], el['type'], el.get('level'), el['uid'], el['ifc'], el['fid'],
                    json.dumps([x.tolist() for x in el['bb']]) if el['bb'] else None) for el in els])
    rows = []
    for el in els:
        for k, v in ctx.par.get(el['id'], {}).get('params', {}).items(): rows.append((el['i'], k, json.dumps(v) if not isinstance(v, str) else v))
    db.executemany('insert into prm values(?,?,?)', rows); db.commit(); db.close()
    meta['buildSecs'] = round(time.time() - t0, 1)
    json.dump(meta, open(os.path.join(outdir, 'meta.json'), 'w'), separators=(',', ':'))
    log('wrote %s in %.1fs: %d batches, %d tris' % (outdir, time.time() - t0, len(batches), sum(b['tris'] for b in bmeta)))
    return meta
