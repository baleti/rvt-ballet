"""rvt -> cache: model.glb (batched by category, per-vertex element index), meta.json (tree, levels, grids, ...), model.sqlite (elements + parameters)."""
import os, sys, json, time, math, sqlite3, hashlib, colorsys, collections
import numpy as np
from . import reader, geom, glb
from .geom import Mesh

FID_ORDER = ['solid', 'param', 'approx', 'bbox', 'line', 'none']      # honesty ladder shown in the UI
FID_LABEL = {'solid': 'decoded B-rep', 'param': 'rebuilt from stored parameters (approximate: no joins/openings)', 'approx': 'footprint from stored curves, height range from the Revit bounding box (slopes not modelled)', 'bbox': 'placeholder at true bounding box', 'line': 'curve', 'none': 'no geometry'}

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

from .build_util import g

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

SYSTEM_FAMILY = {'BasicWallType': 'Basic Wall', 'NewCurtainWallType': 'Curtain Wall', 'StackedWallType': 'Stacked Wall', 'FloorType': 'Floor', 'CompoundCeilingType': 'Compound Ceiling',
                 'RoofType': 'Basic Roof', 'StairsType': 'Stairs', 'RbsPipeType': 'Pipe Types', 'RbsDuctType': 'Duct Types', 'RbsConduitType': 'Conduit', 'RbsCableTrayType': 'Cable Tray'}

def sym_name(ctx, r):
    n = g(r['fields'], 'm_symbolInfo', 'm_name')
    return n if isinstance(n, str) and n else None

def family_name(ctx, tid):
    """Family name of a type element: loaded family via the symbol's m_familyId, else the system-family name for the type class"""
    if tid is None: return None
    r = ctx.recs.get(tid)
    if r is None: return None
    fid = ctx.eid_int(r['fields'].get('m_familyId')) if 'm_familyId' in r['fields'] else None
    if fid is not None and fid in ctx.recs:
        n = ctx.recs[fid]['fields'].get('m_name')
        if isinstance(n, str) and n: return n
    return SYSTEM_FAMILY.get(r['class'])

def build_table(ctx):
    els = []
    for e, r in ctx.recs.items():
        p = ctx.par.get(e, {}).get('params', {})
        tid = type_of(ctx, e, r)
        name = p.get('Name') or p.get('Type Name') or sym_name(ctx, r) or r['fields'].get('m_name') or r['fields'].get('m_text') or r['fields'].get('m_viewName')
        tname = None
        if tid is not None:
            tp = ctx.par.get(tid, {}).get('params', {}); tname = tp.get('Type Name') or tp.get('Name') or sym_name(ctx, ctx.recs[tid]) or ctx.recs[tid]['fields'].get('m_name')
        is_type = ('Type Name' in p or 'm_symbolInfo' in r['fields']) and tid is None and ctx.eid_int(p.get('Type Id')) in (None, e)
        fam = family_name(ctx, tid if tid is not None else (e if is_type else None))
        if is_type and tname is None: tname = name
        els.append({'id': e, 'cls': r['class'], 'cat': ctx.catname(e), 'name': name if isinstance(name, str) else None, 'type': tname if isinstance(tname, str) else None, 'family': fam,
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

def curved_wall_geom(ctx, e, r):
    """curved wall: reference faces are cylinders (center, axes, radius, angle/height envelope); ring sector between the smallest and largest radius"""
    cyl = []
    for fc in r['fields'].get('m_pRefFaces') or []:
        sf = g(fc, 'm_pSurf')
        if isinstance(sf, dict) and 'm_radius' in sf and 'm_zVec' in sf and sf.get('m_Envelope'):
            cyl.append(sf)
    if len(cyl) < 2: return None
    c = np.array(cyl[0]['m_center'], float); x = np.array(cyl[0]['m_xVec'], float); y = np.array(cyl[0]['m_yVec'], float); z = np.array(cyl[0]['m_zVec'], float)
    (u0, v0), (u1, v1) = cyl[0]['m_Envelope']['m_corners']
    radii = [float(sf['m_radius']) for sf in cyl]; r0, r1 = min(radii), max(radii)
    if r1 - r0 < 1e-6: return None
    k = max(4, int(abs(u1 - u0) / np.radians(8)) + 1); t = np.linspace(u0, u1, k + 1)
    if abs(z[2]) < 0.999: return None
    ring = lambda R: c[:2] + R * (np.cos(t)[:, None] * x[:2] + np.sin(t)[:, None] * y[:2])
    outer = ring(r1); inner = ring(r0)
    m = geom.prism([np.vstack([outer, inner[::-1]])], c[2] + v0, c[2] + v1)
    return (m, 'param') if m else None

def wall_geom(ctx, e, r):
    pls = ref_planes(r['fields'])
    if not pls: return curved_wall_geom(ctx, e, r)
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
    """boundary loops (3D points, feet) of the sketch that belongs to element e: the VarSketch/Sketch listed in the element's header parents
    with the highest id below e (a sketch is created just before its element)"""
    h = ctx.eh.get(e); par = g(h, 'm_parents', 'm_deletion') if h else None
    cands = sorted((int(p) for p in par or [] if int(p) in ctx.recs and ctx.recs[int(p)]['class'] in ('VarSketch', 'Sketch') and int(p) < e), reverse=True)
    for pid in cands[:1]:
        r = ctx.recs[pid]
        pairs = g(r['fields'], 'm_elemIdsPairSet', 'm_data') or []
        segs = []
        for it in pairs:
            ce = ctx.recs.get(int(it['m_elementId']))
            if not ce: continue
            s_ = curve_pts(g(ce['fields'], 'm_pCurveDriver', 'm_pCrv'))
            if s_ is not None: segs.append(s_)
        if segs: return geom.chain_loops(segs)
    return None

def curve_pts(c, maxdeg=10):
    """polyline (Nx3, feet) of a decoded curve object: GLine, GArc, GNurbSpline (clamped-uniform assumption), GPolyLine"""
    if not isinstance(c, dict): return None
    if 'obj' in c and 'm_endParams' not in c: c = c['obj']
    if not isinstance(c, dict): return None
    if 'm_dirVec' in c and 'm_endParams' in c and 'm_origin' in c:
        o = np.array(c['m_origin'], float); d = np.array(c['m_dirVec'], float); t0, t1 = c['m_endParams']
        return np.array([o + d * t0, o + d * t1])
    if 'm_radius' in c and 'm_center' in c and 'm_endParams' in c and 'm_xVec' in c:
        t0, t1 = c['m_endParams']; R = float(c['m_radius']); ctr = np.array(c['m_center'], float)
        x = np.array(c['m_xVec'], float); y = np.array(c['m_yVec'], float)
        k = max(2, int(abs(t1 - t0) / math.radians(maxdeg)) + 1); t = np.linspace(t0, t1, k + 1)
        return ctr + R * (np.cos(t)[:, None] * x + np.sin(t)[:, None] * y)
    if 'm_ctrlPoints' in c:
        P = np.array([cp['m_Point'] for cp in c['m_ctrlPoints']], float); deg = int(c.get('m_Degree') or 3)
        if len(P) > deg and not c.get('m_Rational'):
            try:
                from scipy.interpolate import BSpline
                n = len(P); kn = np.concatenate([np.zeros(deg), np.linspace(0, 1, n - deg + 1), np.ones(deg)])
                return BSpline(kn, P, deg)(np.linspace(0, 1, max(16, 4 * n)))
            except Exception: pass
        return P
    return None

def plane_z(pl, ctr):
    o, x, y = pl[0], pl[1], pl[2]; n = np.cross(x, y); n = n / np.linalg.norm(n)
    return (lambda xy: o[2] - (n[0] * (xy[:, 0] - o[0]) + n[1] * (xy[:, 1] - o[1])) / n[2]), n

def slab_geom(ctx, e, r):
    """floor/ceiling/roof-like slab: sketch outline extruded between the lowest and highest near-horizontal reference planes (sloped planes followed exactly)"""
    pls = [p for p in ref_planes(r['fields']) if abs(np.cross(p[1], p[2])[2]) / max(np.linalg.norm(np.cross(p[1], p[2])), 1e-12) > 0.3]
    if len(pls) < 2: return None
    loops = sketch_loops(ctx, e)
    if not loops: return None
    closed = [l for l in loops if len(l) >= 3]
    if not closed: return None
    areas = [abs(0.5 * np.sum(l[:, 0] * np.roll(l[:, 1], -1) - np.roll(l[:, 0], -1) * l[:, 1])) for l in closed]
    order = np.argsort(areas)[::-1]
    outer = closed[order[0]][:, :2]; ctr = outer.mean(0)[None, :]
    fz = [plane_z(p, ctr) for p in pls]
    zl = float(closed[order[0]][:, 2].mean())      # the sketch plane is also a bounding layer (ceilings hang below their reference faces)
    bbz = ctx.bbox(e)
    if bbz is not None and bbz[0][2] - 1e-3 <= zl <= bbz[1][2] + 1e-3: fz.append(((lambda xy, c=zl: np.full(len(xy), c)), None))
    zc = [f(ctr)[0] for f, _ in fz]
    top = fz[int(np.argmax(zc))][0]; bot = fz[int(np.argmin(zc))][0]
    flat = all(abs(n[2]) > 0.99999 for _, n in fz if n is not None)
    if flat and bbz is not None and abs(max(zc) - bbz[1][2]) < 0.02 and bbz[0][2] < min(zc) - 1e-6:       # lowest layer is not among the reference faces: take it from the stored bbox
        zb = float(bbz[0][2]); bot = lambda xy, c=zb: np.full(len(xy), c); zc = zc + [zb]
    if abs(max(zc) - min(zc)) < 1e-6: return None
    holes = [closed[i][:, :2] for i in order[1:] if areas[i] > 1e-6]
    m = geom.prism([outer] + holes, bot, top)
    return (m, 'param') if m else None

def sketch_curves(ctx, sid):
    """curves of a sketch element with their stored slope data: [(pts Nx3, angle, defines_slope, offset)]"""
    sk = ctx.recs.get(sid); out = []
    if not sk: return out
    for it in g(sk['fields'], 'm_elemIdsPairSet', 'm_data') or []:
        ce = ctx.recs.get(int(it['m_elementId']))
        if not ce: continue
        pts = curve_pts(g(ce['fields'], 'm_pCurveDriver', 'm_pCrv'))
        ud = g(ce['fields'], 'm_data', 'm_oUserData') or {}
        if pts is not None: out.append((pts, float(ud.get('m_angle') or 0.0), bool(ud.get('m_definingCurve') or ud.get('m_definesHeight')), float(ud.get('m_offset') or 0.0)))
    return out

def roof_geom(ctx, e, r):
    """footprint roof: footprint prism intersected with one half-space per slope-defining sketch edge (Revit slope = angle stored on the edge, rising inwards from the
    edge's own height); thickness from the stored bounding box. Booleans via OpenCascade. Without slope edges: flat prism in the bbox height range."""
    from . import occ
    f = r['fields']; bb = ctx.bbox(e)
    if bb is None: return None
    curves = sketch_curves(ctx, ctx.eid_int(f.get('m_sketchId')) or -1)
    segs = [c[0] for c in curves] or [p for cl in (f.get('m_curveLoops') or []) for c in (g(cl, 'm_curves') or []) for p in [curve_pts(c)] if p is not None]
    loops = [l for l in geom.chain_loops(segs) if len(l) >= 3]
    if not loops: return None
    areas = [abs(0.5 * np.sum(l[:, 0] * np.roll(l[:, 1], -1) - np.roll(l[:, 0], -1) * l[:, 1])) for l in loops]
    order = np.argsort(areas)[::-1]; outer = loops[order[0]][:, :2]; holes = [loops[i][:, :2] for i in order[1:]]
    sloped = [c for c in curves if c[2] and abs(c[1]) > 1e-6 and len(c[0]) >= 2]
    if not sloped:
        m = geom.prism([outer] + holes, bb[0][2], bb[1][2]); return (m, 'approx') if m else None
    return roof_surface(outer, holes, sloped, bb)

def roof_surface(outer, holes, sloped, bb):
    """roof slab over a footprint: bottom height z(p) = min over slope edges whose perpendicular strip contains p of (z_edge + tan(angle) * distance to the edge line);
    the minimum is the hip/gable surface Revit builds for equal-slope footprint roofs (for a convex footprint it is the exact straight-skeleton height).
    Thickness = bbox top minus the highest point of the bottom surface."""
    from scipy.spatial import Delaunay
    from matplotlib.path import Path as _P
    edges = []; poly = _P(outer)
    for pts, ang, _, off in sloped:
        a_ = pts[0][:2]; b_ = pts[-1][:2]; d = b_ - a_; L = np.linalg.norm(d)
        if L < 1e-6: continue
        u = d / L; nrm = np.array([-u[1], u[0]]); mid = (a_ + b_) / 2
        if not poly.contains_point(mid + 0.05 * nrm): nrm = -nrm          # inward = the side of the edge that lies inside the footprint
        edges.append((a_, nrm, np.tan(ang), float(pts[0][2])))
    def zfun(P):
        z = np.full(len(P), np.inf)
        for a_, nrm, t, z0 in edges:
            dist = (P - a_) @ nrm                              # signed inward distance to the edge line
            z = np.minimum(z, np.where(dist >= -0.05, z0 + t * np.maximum(dist, 0.0), np.inf))      # a slope plane only governs the region on its inner side
        z[~np.isfinite(z)] = min(e[3] for e in edges)
        return z
    def dens(l, h=0.5):
        out = []
        for a_, b_ in zip(l, np.roll(l, -1, axis=0)):
            n = max(1, int(np.linalg.norm(b_ - a_) / h)); out += [a_ + (b_ - a_) * k / n for k in range(n)]
        return np.array(out)
    ring = dens(outer); hr = [dens(h_) for h_ in holes]
    lo = outer.min(0); hi = outer.max(0); step = 0.4
    gx, gy = np.meshgrid(np.arange(lo[0] + step / 2, hi[0], step), np.arange(lo[1] + step / 2, hi[1], step)); G = np.c_[gx.ravel(), gy.ravel()]
    inside = _P(outer).contains_points(G, radius=-0.05)
    for h_ in holes: inside &= ~_P(h_).contains_points(G, radius=0.05)
    pts = np.vstack([ring] + hr + [G[inside]])
    tri = Delaunay(pts).simplices
    cen = pts[tri].mean(1); keep = _P(outer).contains_points(cen)
    for h_ in holes: keep &= ~_P(h_).contains_points(cen)
    tri = tri[keep]
    zb = zfun(pts); dz = float((bb[1][2] - bb[0][2]) - (zb.max() - zb.min()))      # thickness = stored bbox height range minus the slope's own rise
    if not 0.05 <= dz <= 3.0: dz = float(np.clip(dz, 0.05, 3.0))
    n = len(pts); top = np.c_[pts, zb + dz]; bot = np.c_[pts, zb]
    m = Mesh(np.vstack([top, bot]), np.vstack([tri, tri[:, ::-1] + n]))
    for l in [ring] + hr:                                    # boundary side faces
        k = len(l); idx = [int(np.argmin(np.linalg.norm(pts - q, axis=1))) for q in l]
        for i in range(k):
            a_, b_ = idx[i], idx[(i + 1) % k]
            m.f = np.vstack([m.f, [[a_, b_, b_ + n], [a_, b_ + n, a_ + n]]])
    m.v[:, 2] += bb[0][2] - m.v[:, 2].min()          # sketch plane height is only a reference; absolute height comes from the stored bbox
    return (m, 'param')

class LineSet:
    """polylines as GL line segments"""
    def __init__(self, pts):
        pts = np.asarray(pts, float); self.v = pts
        n = len(pts); self.f = np.c_[np.arange(n - 1), np.arange(1, n)].astype(np.int32) if n > 1 else np.zeros((0, 2), np.int32)
    def __bool__(self): return len(self.f) > 0
    kind = 'line'

def mep_geom(ctx, e, r):
    f = r['fields']; c = g(f, 'm_pCurveDriver', 'm_pCrv')
    pts = curve_pts(c)
    if pts is None: return None
    w = f.get('m_dWidthOrDiameter'); h = f.get('m_dHeight'); cls = r['class']
    if not w: return None
    round_ = cls in ('RbsPipeCurve', 'RbsConduitCurve', 'RbsFlexPipeCurve') or (cls in ('RbsDuctCurve', 'RbsFlexDuctCurve') and (not h or h <= 0))
    if cls == 'RbsPipeCurve':
        dpm = g(f, 'm_pDesignPropManager') or {}
        od = dpm.get('m_dOuterDiameter') if isinstance(dpm, dict) else None
        if od: w = od
    m = Mesh()
    for a_, b_ in zip(pts[:-1], pts[1:]):
        m.add(geom.tube(a_, b_, w / 2, 14) if round_ else geom.rect_tube(a_, b_, w, h or w))
    return (m, 'param') if m else None

def line_geom(ctx, e, r):
    pts = curve_pts(g(r['fields'], 'm_pCurveDriver', 'm_pCrv'))
    return (LineSet(pts), 'line') if pts is not None and len(pts) > 1 else None

def inst_frame(ctx, r):
    ii = g(r['fields'], 'm_pInstanceInfo'); trf = g(ii, 'm_Trf') if ii else None
    if not trf: return None
    M = np.array(trf['m_3x3'], float); o = np.array(trf['m_or'], float)
    return M, o

def instance_box(ctx, e, r):
    """placeholder for a family instance: box at the true location/orientation. The world bounding box from the element header is exact;
    for rotated instances the oriented box is fitted so that its world AABB matches the header box (stretched axes are solved by NNLS)."""
    bb = ctx.bbox(e)
    if bb is None: return None
    lo, hi = bb; A = hi - lo
    fr = inst_frame(ctx, r)
    sym = ctx.eid_int(r['fields'].get('m_masterSymbolId')); sb = ctx.bbox(sym) if sym is not None else None
    if fr is None or sb is None: return geom.box(lo, hi), 'bbox'
    M, o = fr
    # world = M @ local (columns are the local axes) or M.T; pick the orientation consistent with the header box
    cands = []
    for MM in (M, M.T):
        if np.all(np.abs(np.abs(MM) - np.round(np.abs(MM))) < 1e-3): cands.append((0, MM)); continue
        e0 = sb[1] - sb[0]
        from scipy.optimize import nnls
        lam = 0.15
        Aug = np.vstack([np.abs(MM), lam * np.eye(3)]); b = np.concatenate([A, lam * e0])
        ext, _ = nnls(Aug, b)
        err = np.linalg.norm(np.abs(MM) @ ext - A)
        cands.append((err, MM, ext))
    cands.sort(key=lambda t: t[0])
    best = cands[0]
    if len(best) == 2: return geom.box(lo, hi), 'bbox'          # axis-aligned: header box is exact
    err, MM, ext = best
    if err > 0.25 * max(np.linalg.norm(A), 1e-6): return geom.box(lo, hi), 'bbox'
    c = (lo + hi) / 2
    m = geom.box(-ext / 2, ext / 2); m.v = m.v @ MM.T + c
    return m, 'bbox'

LINE_CLASSES = {'CurveElem'}
BUILDERS = {'ProfileRoof': roof_geom, 'FootPrintRoof': roof_geom, 'SWall': wall_geom, 'Floor': slab_geom, 'Ceiling': slab_geom, 'RoofSoffit': slab_geom, 'BuildingPad': slab_geom, 'RbsDuctCurve': mep_geom, 'RbsPipeCurve': mep_geom, 'RbsConduitCurve': mep_geom, 'CableTray': mep_geom,
            'RbsFlexDuctCurve': mep_geom, 'RbsFlexPipeCurve': mep_geom, 'CurveElem': line_geom, 'FamilyInstance': instance_box}
HIDE_DEFAULT_CATS = {'Center line', '<Sketch>', 'Work Plane Grid', 'Cameras', 'Scope Boxes', 'Boundary Conditions', 'Area Loads', 'Line Loads', 'Point Loads', 'Division Profiles',
                     'Survey Point', 'Project Base Point', 'Internal Origin', 'Guide Grid', 'Reference Planes', 'Parts', 'Spaces', 'Rooms', 'Areas', 'Mass Floor', 'RVT Links', 'Analytical Nodes', 'Reference Points', 'Grids', 'Levels', 'Sections', 'Viewports'}
TRANSLUCENT_CATS = {'Planting', 'Entourage', 'Mass', 'Rooms', 'Spaces', 'Areas', 'Scope Boxes', 'Mass Floor', 'RVT Links'}

def default_hidden(cat): return cat in HIDE_DEFAULT_CATS or cat.startswith('Analytical')

def box_iou(lo1, hi1, lo2, hi2):
    lo = np.maximum(lo1, lo2); hi = np.minimum(hi1, hi2); d = np.maximum(hi - lo, 0)
    inter = float(np.prod(d)); a = float(np.prod(np.maximum(hi1 - lo1, 1e-6))); b = float(np.prod(np.maximum(hi2 - lo2, 1e-6)))
    return inter / (a + b - inter) if a + b - inter > 0 else 0.0

def brep_geom(ctx, e, r):
    """decoded planar B-rep bodies stored in the element (stairs runs, some floors/families). Needs >= 4 faces per body; rejected if far from the header box."""
    from . import brep
    if r['class'].startswith(('DBView', 'Analytical')): return None
    gs = [x for x in brep.find_geometries(r['fields']) if len(x['m_pFaces']) >= 4]
    if not gs: return None
    m = Mesh(); npl = 0; nsk = 0
    for gm in gs:
        mm, n, sk = brep.geometry_mesh(gm); m.add(mm); npl += n; nsk += sk
    if not m: return None
    bb = ctx.bbox(e)
    if bb is not None and box_iou(m.v.min(0), m.v.max(0), *bb) < 0.5: return None
    return m, ('solid' if nsk == 0 else 'partial')

def element_mesh(ctx, e, r):
    if ctx.catname(e) in ('Planting', 'Entourage') and ctx.bbox(e) is not None and r['class'] == 'FamilyInstance': return geom.ellipsoid(*ctx.bbox(e)), 'bbox'
    try:
        res = brep_geom(ctx, e, r)
        if res and res[0] and res[1] == 'solid': return res
        part = res if res and res[0] else None
    except Exception as ex:
        if os.environ.get('RVT_DEBUG'): print('brep', r['class'], e, repr(ex))
    fn = BUILDERS.get(r['class'])
    if fn:
        try:
            res = fn(ctx, e, r)
            if res and res[0]: return res
        except Exception as ex:
            if os.environ.get('RVT_DEBUG'): print('builder', r['class'], e, repr(ex))
    if part: return part[0], 'approx'
    if ctx.catname(e) in ('Planting', 'Entourage') and ctx.bbox(e) is not None: return geom.ellipsoid(*ctx.bbox(e)), 'bbox'          # some faces of the decoded body are of an unsupported surface type
    bb = ctx.bbox(e)
    if bb is not None: return geom.box(*bb), 'bbox'
    return None

# ---------------------------------------------------------------- datum / spatial

def build_levels(ctx):
    out = []; seen = set()
    for e, (n, z) in ctx.levels.items():
        if z is None or (n, round(z, 4)) in seen: continue          # copies owned by groups / design options repeat name + elevation
        seen.add((n, round(z, 4))); out.append({'id': e, 'name': n, 'elev': z * 0.3048})
    return sorted(out, key=lambda l: l['elev'])

def build_grids(ctx):
    """grid lines: the Grid element stores a vertical datum plane (origin, x along the line, y up) with an extent envelope [(u0,v0),(u1,v1)]"""
    out = []
    for e, r in ctx.recs.items():
        if r['class'] != 'Grid': continue
        pl = plane_of(g(r['fields'], 'm_pSurface'))
        pts = None
        if pl and pl[3]:
            o, x, y, env = pl; (u0, v0), (u1, v1) = env
            pts = np.array([o + x * u0 + y * v0, o + x * u1 + y * v0])
        if pts is None: continue
        out.append({'id': e, 'name': r['fields'].get('m_text', ''), 'pts': [[round(float(a) * 0.3048, 4) for a in p] for p in pts]})
    return out

# ---------------------------------------------------------------- main

def convert(path, outdir, log=print):
    t0 = time.time(); os.makedirs(outdir, exist_ok=True)
    raw = reader.cached_load(path, log); ctx = Ctx(raw)
    from . import datums
    els = build_table(ctx); log('%d elements' % len(els))
    levels = build_levels(ctx); lvl_by_id = {e: n for e, (n, z) in ctx.levels.items()}
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
    acc = {}; covg = collections.defaultdict(collections.Counter); ious = {}
    for i, el in enumerate(els):
        el['i'] = i; r = ctx.recs[el['id']]
        res = element_mesh(ctx, el['id'], r) if (el['cat'] and not el['isType']) else None
        if res is None:
            covg[el['cat'] or '(none)']['none'] += 1; continue
        mesh, fid = res
        el['fid'] = fid; covg[el['cat']][fid] += 1
        if fid in ('param', 'solid') and el['bb'] is not None:
            el['iou'] = round(box_iou(mesh.v.min(0), mesh.v.max(0), *el['bb']), 3); ious.setdefault(el['cat'], []).append(el['iou'])
        kind = getattr(mesh, 'kind', 'tri'); transl = fid == 'bbox' and el['cat'] in TRANSLUCENT_CATS
        a = acc.setdefault((el['cat'], kind, transl), {'pos': [], 'idx': [], 'eidx': [], 'ranges': [], 'nv': 0, 'nt': 0})
        a['pos'].append(mesh.v); a['idx'].append(mesh.f.reshape(-1) + a['nv']); a['eidx'].append(np.full(len(mesh.v), i, np.float32))
        a['ranges'] += [i, a['nt'], len(mesh.f)]; a['nv'] += len(mesh.v); a['nt'] += len(mesh.f)
    batches = []; bmeta = []
    for (cat, kind, transl), a in acc.items():
        pos = glb.to_yup_m(np.vstack(a['pos'])); idx = np.concatenate(a['idx']).astype(np.uint32)
        c = (0.1, 0.1, 0.12) if kind == 'line' else cat_color(cat)
        alpha = 0.45 if cat in ('Windows', 'Curtain Panels') else ((0.08 if cat in ('Planting', 'Entourage') else 0.18) if transl else 1.0)
        batches.append({'name': cat + ('' if kind == 'tri' else ' (lines)'), 'color': (*c, alpha), 'pos': pos, 'eidx': np.concatenate(a['eidx']), 'idx': idx, 'mode': 1 if kind == 'line' else 4})
        bmeta.append({'cat': cat, 'kind': kind, 'color': '#%02x%02x%02x' % tuple(int(x * 255) for x in c), 'alpha': alpha, 'ranges': a['ranges'], 'tris': a['nt']})
    glb.write_glb(os.path.join(outdir, 'model.glb'), batches)
    allb = [el['bb'] for el in els if el['bb'] is not None and el['fid'] != 'none' and not default_hidden(el['cat'] or '') and el['cat'] not in ('Mass',)]
    if not allb: allb = [el['bb'] for el in els if el['bb'] is not None and el['fid'] != 'none']
    if allb:
        lo = np.percentile([b[0] for b in allb], 0.5, axis=0) * 0.3048; hi = np.percentile([b[1] for b in allb], 99.5, axis=0) * 0.3048
        lo = np.minimum(lo, np.min([b[0] for b in allb], 0) * 0.3048 if len(allb) < 50 else lo); hi = np.maximum(hi, np.max([b[1] for b in allb], 0) * 0.3048 if len(allb) < 50 else hi)
    else: lo = hi = np.zeros(3)
    views, sheets = datums.views_sheets(ctx)
    meta = {'file': os.path.basename(path), 'levels': levels, 'grids': build_grids(ctx), 'batches': bmeta, 'rooms': datums.rooms(ctx, lvl_by_id), 'views': views, 'sheets': sheets,
            'bbox': [lo.tolist(), hi.tolist()], 'fidLabels': FID_LABEL, 'defaultHidden': sorted({el['cat'] for el in els if el['cat'] and default_hidden(el['cat'])}),
            'elements': [[el['id'], el['cls'], el['cat'], el['name'], el['type'], el['level'], el['fid'], el['isType'], el['family']] for el in els],
            'stamps': {'reader': reader.reader_stamp(), 'viewer': reader.viewer_stamp()}, 'coverage': {k: dict(v) for k, v in covg.items()}, 'bboxAgreement': {k: [round(float(np.mean(v)), 3), len(v)] for k, v in ious.items()}, 'built': time.time(), 'buildSecs': 0}
    for r_ in meta['rooms']:
        for el in els:
            if el['id'] == r_['id']: r_['i'] = el['i']; break
    dbp = os.path.join(outdir, 'model.sqlite')
    if os.path.exists(dbp): os.remove(dbp)
    db = sqlite3.connect(dbp)
    db.executescript('create table el(i integer primary key, id integer, cls text, cat text, name text, type text, family text, level text, uid text, ifc text, fid text, bb text, iou real);'
                     'create table prm(i integer, k text, v text);create index prm_i on prm(i);')
    db.executemany('insert into el values(?,?,?,?,?,?,?,?,?,?,?,?,?)', [(el['i'], el['id'], el['cls'], el['cat'], el['name'], el['type'], el['family'], el.get('level'), el['uid'], el['ifc'], el['fid'],
                    json.dumps([x.tolist() for x in el['bb']]) if el['bb'] else None, el.get('iou')) for el in els])
    rows = []
    for el in els:
        for k, v in ctx.par.get(el['id'], {}).get('params', {}).items():
            if isinstance(v, int) and not isinstance(v, bool): v = ctx.sc(v) if v >= (1 << (8 * ctx.W - 1)) else int(v)
            rows.append((el['i'], k, json.dumps(v) if not isinstance(v, str) else v))
    db.executemany('insert into prm values(?,?,?)', rows); db.commit(); db.close()
    meta['buildSecs'] = round(time.time() - t0, 1)
    json.dump(meta, open(os.path.join(outdir, 'meta.json'), 'w'), separators=(',', ':'))
    log('wrote %s in %.1fs: %d batches, %d tris' % (outdir, time.time() - t0, len(batches), sum(b['tris'] for b in bmeta)))
    return meta
