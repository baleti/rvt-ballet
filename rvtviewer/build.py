"""rvt -> cache: model.glb (batched by category, per-vertex element index), meta.json (tree, levels, grids, ...), model.sqlite (elements + parameters)."""
import os, sys, json, time, math, sqlite3, hashlib, colorsys, collections
import numpy as np
from . import reader, geom, glb
from .geom import Mesh

FID_ORDER = ['solid', 'mesh', 'matched', 'param', 'approx', 'bbox', 'line', 'void', 'none']      # honesty ladder shown in the UI
FID_LABEL = {'solid': 'decoded B-rep (true geometry from the element\'s own faces)', 'mesh': 'triangle mesh Revit saved with the element (true geometry; planar + cylindrical faces)', 'matched': 'rebuilt from stored data; extents agree with the bounding box Revit stored (IoU >= 0.97, or inside it spanning >= 93% of its two largest dimensions)', 'param': 'rebuilt from stored parameters (approximate: no joins/openings)', 'approx': 'footprint from stored curves, height range from the Revit bounding box (slopes not modelled)', 'bbox': 'placeholder at true bounding box', 'line': 'curve', 'void': 'no 3D solid in Revit either (void-only opening / reference family, Revit Volume 0): stored bounding box drawn as an outline', 'none': 'no geometry'}

CAT_COLORS = {
    'Walls': (0.82, 0.80, 0.76), 'Floors': (0.70, 0.66, 0.60), 'Roofs': (0.60, 0.35, 0.30), 'Ceilings': (0.90, 0.90, 0.88),
    'Structural Columns': (0.55, 0.60, 0.68), 'Structural Framing': (0.50, 0.62, 0.78), 'Structural Foundations': (0.55, 0.50, 0.45),
    'Ducts': (0.30, 0.65, 0.85), 'Duct Fittings': (0.25, 0.55, 0.75), 'Flex Ducts': (0.40, 0.72, 0.88), 'Pipes': (0.30, 0.80, 0.45), 'Pipe Fittings': (0.25, 0.65, 0.40),
    'Conduits': (0.85, 0.65, 0.25), 'Cable Trays': (0.90, 0.75, 0.30), 'Doors': (0.62, 0.45, 0.30), 'Windows': (0.55, 0.78, 0.90),
    'Stairs': (0.75, 0.72, 0.65), 'Railings': (0.60, 0.60, 0.62), 'Furniture': (0.78, 0.60, 0.45), 'Plumbing Fixtures': (0.85, 0.88, 0.92),
    'Lighting Fixtures': (0.98, 0.90, 0.50), 'Mechanical Equipment': (0.45, 0.70, 0.55), 'Electrical Equipment': (0.90, 0.55, 0.30),
    'Curtain Panels': (0.60, 0.80, 0.90), 'Curtain Wall Mullions': (0.50, 0.52, 0.55), 'Structural Rebar': (0.75, 0.30, 0.25), 'Topography': (0.55, 0.62, 0.45),
    'Lines': (0.2, 0.2, 0.2), 'Planting': (0.36, 0.52, 0.30), 'Entourage': (0.55, 0.56, 0.60), 'Pads': (0.62, 0.60, 0.55), 'Site': (0.55, 0.55, 0.50), 'Parking': (0.45, 0.45, 0.47),
    'Air Terminals': (0.86, 0.87, 0.90), 'Duct Accessories': (0.55, 0.62, 0.70), 'Pipe Accessories': (0.45, 0.60, 0.48), 'Sprinklers': (0.85, 0.30, 0.25), 'Plumbing Equipment': (0.75, 0.78, 0.82),
    'Electrical Fixtures': (0.92, 0.80, 0.45), 'Communication Devices': (0.80, 0.75, 0.60), 'Fire Alarm Devices': (0.88, 0.35, 0.30), 'Conduit Fittings': (0.80, 0.60, 0.25), 'Cable Tray Fittings': (0.85, 0.70, 0.28),
    'Generic Models': (0.72, 0.70, 0.68), 'Casework': (0.80, 0.70, 0.55), 'Specialty Equipment': (0.70, 0.70, 0.72), 'Columns': (0.80, 0.78, 0.74), 'Fascias': (0.85, 0.84, 0.80), 'Gutters': (0.70, 0.70, 0.72),
}
def cat_color(name):
    c = CAT_COLORS.get(name)
    if c: return c
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16) / 0xffffff
    return colorsys.hls_to_rgb(h, 0.62, 0.35)

from .build_util import g

HOSTED_CUT_CATS = ('Doors', 'Windows', 'Generic Models')

USE_SYMBOL_CUTS = True
OPENING_SHRINK = {'Doors': 0.2, 'Windows': 0.2}
OPENING_SHRINK_Z = {'Doors': 0.2, 'Windows': 0.2}  # old:      # ft trimmed from each side of a hosted instance's bbox to get the actual hole (frame/casing)
ROOF_ATTACH_FRACTION = 1.0      # measured against Revit wall volumes: wall tops joined to a roof reach the roof's top surface (0 = underside)

class Ctx:
    def __init__(self, raw):
        self.raw = raw; self.W = raw['W']; self.names = raw['classes']
        self.recs = {}; self.cls_of = {}
        for (e, c), r in raw['recs'].items():
            if e not in self.recs: self.recs[e] = r
        self.eh = raw['eh']; self.par = raw['params']
        self.cat = reader.category_names()
        self.hosted = collections.defaultdict(list)      # host element id -> hosted door/window instance ids (openings)
        for e, r in self.recs.items():
            if r['class'] == 'FamilyInstance' and r['fields'].get('m_hostId') is not None:
                h = self.eid_int(r['fields']['m_hostId'])
                if h is not None and self.catname(e) in HOSTED_CUT_CATS: self.hosted[h].append(e)
        self._bb = {}; self._cutcache = {}; self._why = {}
        self.roof_fields = {}      # roof id -> (footprint Path, bottom-surface height function (xy Nx2 -> z)), filled by roof_geom
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
        c = self._bb.get(e, 0)
        if c != 0: return c
        h = self.eh.get(e); bb = g(h, 'm_pBBox', 'm_minmax') if h else None
        res = None
        if bb:
            a, b = bb[0], bb[1]
            if all(abs(x) <= 1e8 for x in a) and all(abs(x) <= 1e8 for x in b) and all(b[k] >= a[k] for k in range(3)): res = (np.array(a, float), np.array(b, float))
        self._bb[e] = res; return res
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

def material_rgb(ctx, mid):
    r = ctx.recs.get(mid) if mid is not None else None
    c = g(r['fields'], 'm_pMaterial', 'm_color') if r else None
    if c is None: return None
    c = int(c); return ((c & 255) / 255.0, ((c >> 8) & 255) / 255.0, ((c >> 16) & 255) / 255.0)

def type_layers(ctx, tid):
    """compound-structure layers of a wall/floor/roof type: [(width ft, function, rgb or None)] exterior side first"""
    r = ctx.recs.get(tid) if tid is not None else None
    cs = g(r['fields'], 'm_pCompoundStructure') if r else None
    out = []
    for L in (cs or {}).get('m_layers') or []:
        w = float(L.get('m_layerWidth') or 0)
        if w > 1e-6: out.append((w, int(L.get('m_layerFunction') or 0), material_rgb(ctx, ctx.eid_int(L.get('m_materialId')))))
    return out

CORE_GRAY = (0.62, 0.62, 0.60)
def dominant_rgb(layers):
    if not layers: return None
    best = max(layers, key=lambda L: (L[2] is not None, L[0]))     # widest layer that has a material
    return best[2]

CLASS_CAT = {'SiteSurface': 'Topography', 'ArcWall': 'Walls', 'SWall': 'Walls', 'Floor': 'Floors', 'Ceiling': 'Ceilings', 'ProfileRoof': 'Roofs', 'FootPrintRoof': 'Roofs', 'RbsDuctCurve': 'Ducts', 'RbsPipeCurve': 'Pipes',
             'ExtrusionElem': 'Family forms', 'SweepElem': 'Family forms', 'BlendElem': 'Family forms', 'RevolutionElem': 'Family forms', 'SweptBlendElem': 'Family forms'}      # elements the file stores without an ElementHeader (no category / bbox); family-editor forms (.rfa) carry no category

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
        els.append({'id': e, 'cls': r['class'], 'cat': ctx.catname(e) or CLASS_CAT.get(r['class']), 'name': name if isinstance(name, str) else None, 'type': tname if isinstance(tname, str) else None, 'family': fam,
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
    res = wall_solid(ctx, e, r)
    if res is None: return None
    return res

def wall_frame(ctx, e, r):
    """straight wall frame from the reference faces: (o0, x0 along the wall, n across, y0 up, ext[2][3] = min/max (along, across, up) relative to o0)"""
    pls = [p for p in ref_planes(r['fields']) if p[3]]
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
    ext = full_thickness(ctx, e, r, pls, o0, n, ext)
    return o0, x0, n, y0, ext

def full_thickness(ctx, e, r, pls, o0, n, ext):
    """the reference faces can omit outer finish layers: extend the across-extent to the type's full compound-structure width, placing the layer boundaries so that as many reference-face offsets as possible coincide with boundaries"""
    lay = type_layers(ctx, type_of(ctx, e, r)); W = sum(L[0] for L in lay)
    lo, hi = float(ext[0][1]), float(ext[1][1])
    if W <= hi - lo + 1e-4 or len(lay) < 2: return ext
    R = sorted({round(float(np.dot(p[0] - o0, n)), 5) for p in pls}); cum = [0.0]
    for L in lay: cum.append(cum[-1] + L[0])
    best = None
    for rev in (False, True):
        B = [W - c for c in cum][::-1] if rev else cum
        for ri in R:
            for b in B:
                st = ri - b; score = sum(1 for rj in R if any(abs(rj - (st + bb)) < 2e-3 for bb in B))
                contains = st <= lo + 2e-3 and st + W >= hi - 2e-3
                key = (contains, score, -abs(st - lo))
                if best is None or key > best[0]: best = (key, st)
    if best is None or not best[0][0]: return ext
    out = ext.copy(); out[0][1] = best[1]; out[1][1] = best[1] + W; return out

def wall_end_joins(ctx, e, r, fr):
    """corner joins at the two wall ends: [None | (cut plane point Q, keep-side normal, extension length)] for end 0 and end 1. Revit trims a joined wall end at the miter line
    through the intersections of the two walls' face lines (outer-outer, inner-inner); the wall is first extended past its location-line end, then cut."""
    out = [None, None]
    o0, x0, n, y0, ext = fr
    drv = g(r['fields'], 'm_pCurveDriver') or {}
    for it in drv.get('m_controlJoinsSet') or []:
        info = it.get('obj', it); ji = info.get('m_JoinInfo', info); k = int(info.get('m_index', -1))
        if k not in (0, 1): continue
        others = [x for x in (ji.get('m_info') or []) if int(x['m_elemId']) != e]
        if len(others) != 1: continue
        b = int(others[0]['m_elemId']); jb = int(others[0]['m_joinedEnd']); rb = ctx.recs.get(b)
        if not rb or rb['class'] != 'SWall': continue
        fb = wall_frame(ctx, b, rb)
        if fb is None: continue
        ob, xb, nb, yb, eb = fb
        # plan geometry (xy): the two strips' face lines
        def lines(o, x, nrm, ex): return [(o[:2] + nrm[:2] * ex[0][1], x[:2]), (o[:2] + nrm[:2] * ex[1][1], x[:2])]
        LA = lines(o0, x0, n, ext); LB = lines(ob, xb, nb, eb)
        pa = o0[:2] + x0[:2] * (ext[0][0] if k == 0 else ext[1][0]); pb_ = ob[:2] + xb[:2] * (eb[0][0] if jb == 0 else eb[1][0])
        P = (pa + pb_) / 2
        a = x0[:2] * (1 if k == 0 else -1); bdir = xb[:2] * (1 if jb == 0 else -1)           # unit vectors from the joint into each wall body
        cross = abs(a[0] * bdir[1] - a[1] * bdir[0])
        if cross < 0.05: continue                                                        # collinear: plain end
        if cross > 0.985:                                                                # perpendicular butt join: the first wall listed at the joint runs through to the far face of the other wall, the others stop at its near face
            first = int(g(it, 'm_JoinInfo', 'm_info')[0]['m_elemId']) == e if g(it, 'm_JoinInfo', 'm_info') else True
            ub = sorted(float(np.dot(ob + nb * ex_ - o0, x0)) for ex_ in (eb[0][1], eb[1][1]))
            near, far = (ub[0], ub[1]) if k == 1 else (ub[1], ub[0])
            out[k] = {'u': far if first else near}; continue
        Qs = []
        for (p1, d1) in LA:
            for (p2, d2) in LB:
                M = np.array([d1, -d2]).T
                try: t = np.linalg.solve(M, p2 - p1)
                except np.linalg.LinAlgError: continue
                Qs.append(p1 + d1 * t[0])
        if len(Qs) != 4: continue
        sc = [np.dot(q - P, a + bdir) for q in Qs]; Qout = Qs[int(np.argmin(sc))]; Qin = Qs[int(np.argmax(sc))]
        m = Qin - Qout
        if np.linalg.norm(m) < 1e-6: continue
        m /= np.linalg.norm(m); keep = a - np.dot(a, m) * m
        if np.linalg.norm(keep) < 1e-6: continue
        keep /= np.linalg.norm(keep)
        out[k] = {'miter': (np.array([Qout[0], Qout[1], 0.0]), np.array([keep[0], keep[1], 0.0]), float(abs(ext[1][1] - ext[0][1]) + abs(eb[1][1] - eb[0][1])) + 0.5)}
    return out

def wall_solid(ctx, e, r):
    if not ref_planes(r['fields']): return curved_wall_geom(ctx, e, r)
    fr = wall_frame(ctx, e, r)
    if fr is None: return None
    o0, x0, n, y0, ext = fr
    d = ext[1] - ext[0]
    org = o0 + x0 * ext[0][0] + n * ext[0][1] + y0 * ext[0][2]
    joins = wall_end_joins(ctx, e, r, fr)
    if any(j and 'u' in j for j in joins):                     # butt joins only move the end positions
        u0 = joins[0]['u'] if joins[0] and 'u' in joins[0] else ext[0][0]; u1 = joins[1]['u'] if joins[1] and 'u' in joins[1] else ext[1][0]
        if u1 - u0 > 0.05:
            org = o0 + x0 * u0 + n * ext[0][1] + y0 * ext[0][2]; d = np.array([u1 - u0, d[1], d[2]])
    joins = [j if j and 'miter' in j else None for j in joins]
    holes = wall_openings(ctx, e, org, x0, n, y0, d)
    prof = wall_edit_profile(ctx, e, r, o0, x0, n, y0, ext, d)           # wall with an edited elevation profile (sketch loop)
    if prof is None: prof = wall_top_profile(ctx, e, r, org, x0, n, y0, d)
    if prof is not None: joins = [None, None]
    tid = type_of(ctx, e, r); layers = type_layers(ctx, tid)
    flipped = bool(r['fields'].get('m_isFlipped'))
    solid = None
    if prof is not None or holes or len(layers) > 1 or any(joins):
        try:
            from . import occ
            if prof is not None: w = occ.extrude_polygon(prof, n * d[1])
            else:
                e0 = joins[0]['miter'][2] if joins[0] else 0.0; e1 = joins[1]['miter'][2] if joins[1] else 0.0
                w = occ.box_frame(org - x0 * e0, x0 * (d[0] + e0 + e1), n * d[1], y0 * d[2])
                for jn in joins:
                    if jn: w = occ.cut(w, occ.halfspace_below(np.array([jn['miter'][0][0], jn['miter'][0][1], org[2]]), jn['miter'][1]))
            for ho in holes: w = occ.cut(w, ho)
            solid = w
        except Exception as ex:
            if os.environ.get('RVT_DEBUG'): print('wall solid failed', e, repr(ex))
    if solid is not None and len(layers) > 1:
        try:
            from . import occ
            tot = sum(L[0] for L in layers); parts = []; cum = 0.0
            seq = layers if not flipped else layers[::-1]            # exterior layer first; exterior is the -n side of the reference-face frame (wall direction x, left = exterior)
            for wd, fn, rgb in seq:
                t0 = cum / tot * d[1]; t1 = (cum + wd) / tot * d[1]; cum += wd
                slab = occ.box_frame(org - x0 * 6.0 - y0 * 1.0 + n * t0, x0 * (d[0] + 12.0), n * (t1 - t0), y0 * (d[2] + 60.0))
                parts.append((occ.to_mesh(occ.common(solid, slab)), rgb or CORE_GRAY))
            mu = geom.Multi(parts)
            if mu: return mu, 'param'
        except Exception as ex:
            if os.environ.get('RVT_DEBUG'): print('layer split failed', e, repr(ex))
    col = dominant_rgb(layers) or None
    if solid is not None:
        try:
            from . import occ
            m = occ.to_mesh(solid)
            if m: return (geom.Multi([(m, col)]) if col else m), 'param'
        except Exception as ex:
            if os.environ.get('RVT_DEBUG'): print('wall mesh failed', e, repr(ex))
    m = geom.obox(org, x0 * d[0], n * d[1], y0 * d[2])
    return (geom.Multi([(m, col)]) if col else m), 'param'

def wall_edit_profile(ctx, e, r, o0, x0, n, y0, ext, d):
    """Edit Profile walls: the elevation outline is a sketch of lines/arcs in the wall plane (VarSketch owned via the header parents / created just before the wall; step ExtrusionGStep). -> closed polygon (3D points on the wall's lower face plane) or None"""
    gs = g(r['fields'], 'm_geomSteps') or {}
    names = ctx.names if hasattr(ctx, 'names') else None
    has = False
    for lst in ('m_bRepFormGList', 'm_bRepAdjustGList'):
        for st in gs.get(lst) or []:
            if isinstance(st, dict) and names and names[st['ptr'] - 12] == 'ExtrusionGStep': has = True
    if not has: return None
    loops = sketch_loops(ctx, e)
    if not loops:                                   # walls without an ElementHeader: the profile sketch is created next to the wall (nearest VarSketch id whose curves lie in the wall plane)
        for sid in sorted((i for i, rr in ctx.recs.items() if rr['class'] == 'VarSketch' and e - 3 <= i <= e + 12), key=lambda i: abs(i - e)):
            segs = [curve_pts(g(ctx.recs[int(it['m_elementId'])]['fields'], 'm_pCurveDriver', 'm_pCrv')) for it in (g(ctx.recs[sid]['fields'], 'm_elemIdsPairSet', 'm_data') or []) if int(it['m_elementId']) in ctx.recs]
            segs = [q for q in segs if q is not None]
            if segs and all(abs(float(np.dot(q - o0, n)) - ext[0][1]) < max(ext[1][1] - ext[0][1], 0.1) + 0.5 for q in np.vstack(segs)): loops = geom.chain_loops(segs); break
    if not loops: return None
    L = [l for l in loops if len(l) >= 3]
    if not L: return None
    big = max(L, key=lambda l: abs(0.5 * np.sum(np.cross(l - l.mean(0), np.roll(l - l.mean(0), -1, axis=0)), axis=0)[:3] @ n) if False else float(np.linalg.norm(l.max(0) - l.min(0))))
    # keep points in the wall plane: project onto the lower face plane (across-coordinate = ext[0][1])
    pts = [p + n * (ext[0][1] - float(np.dot(p - o0, n))) for p in big]
    return [np.asarray(q, float) for q in pts]

def ensure_roofs(ctx):
    if getattr(ctx, '_roofs_done', False): return
    ctx._roofs_done = True
    for e, r in ctx.recs.items():
        if r['class'] in ('ProfileRoof', 'FootPrintRoof'):
            try: roof_geom(ctx, e, r)
            except Exception: pass

def wall_top_profile(ctx, e, r, org, x0, n, y0, d):
    """wall whose top is attached to a roof: polygon in the wall plane (3D points) whose top edge follows the roof's bottom surface along the wall's mid-plane"""
    if abs(y0[2]) < 0.999: return None
    gs = g(r['fields'], 'm_geomSteps') or {}
    roofs = []
    for lst in ('m_bRepFormGList', 'm_bRepAdjustGList', 'm_bRepTweakGList'):
        for st in gs.get(lst) or []:
            o = st.get('obj') if isinstance(st, dict) else None
            if o and 'm_ids' in o and 'm_baseOrTop' in o and int(o['m_baseOrTop']) == 1: roofs += [int(i) for i in o['m_ids']]     # JoinToRoofGStep: top joined to these roofs
    if not roofs: return None
    ensure_roofs(ctx)
    fields = [ctx.roof_fields[i] for i in roofs if i in ctx.roof_fields]
    if not fields: return None
    us = np.unique(np.concatenate([np.arange(0, d[0], 0.25), [d[0]]]))
    mid = org + n * d[1] / 2
    P = (mid[None, :2] + us[:, None] * x0[None, :2])
    top = np.full(len(us), org[2] + d[2]); hit = False
    for poly, zf in fields:
        inside = poly.contains_points(P, radius=0.3)
        if inside.any():
            z = zf(P); top = np.where(inside, z, top); hit = True          # attached wall runs up to the roof underside (the reference faces only know the unattached height)
    if not hit: return None
    top = np.maximum(top, org[2] + 0.05)
    pts = [org, org + x0 * d[0]] + [np.array([*(mid[:2] + u * x0[:2] - n[:2] * d[1] / 2), z]) for u, z in zip(us[::-1], top[::-1])]
    pts = [np.asarray(q, float) for q in pts]
    return pts

def symbol_cut_points(ctx, sid):
    """vertices (symbol-local, feet) of the closed cut bodies (m_complexCutGeoms: the void shapes a family cuts into its host), via the reader's shell split"""
    if sid in ctx._cutcache: return ctx._cutcache[sid]
    pts = None; r = ctx.recs.get(sid)
    try:
        reader._import(); import rvt_mesh
        bodies = []
        for gm in (r['fields'].get('m_complexCutGeoms') or []) if r else []:
            for comp in rvt_mesh.components(gm.get('obj', gm)):
                if comp['tris'] and comp.get('closed') and not comp['unsupported']: bodies.append(np.array(comp['tris'], float).reshape(-1, 3))
        if bodies: pts = np.vstack(bodies)
    except Exception: pts = None
    ctx._cutcache[sid] = pts; return pts

def void_geometry(ctx, e, r):
    """void family instances (cut bodies in m_complexCutGeoms, nothing in the saved graphics): the void shape itself at the instance transform. -> (Mesh, 'mesh') flagged 'void' (drawn translucent) or None"""
    sid = ctx.eid_int(r['fields'].get('m_masterSymbolId')); fr_ = inst_frame(ctx, r); sr = ctx.recs.get(sid) if sid is not None else None
    if not fr_ or not sr: return None
    try:
        reader._import(); import rvt_mesh
        T = []
        for gm in sr['fields'].get('m_complexCutGeoms') or []:
            for comp in rvt_mesh.components(gm.get('obj', gm)):
                if comp['tris'] and not comp['unsupported']: T.append(np.array(comp['tris'], float).reshape(-1, 3))
    except Exception: return None
    if not T: return None
    P = np.vstack(T) @ fr_[0].T + fr_[1]; m = Mesh(P, np.arange(len(P)).reshape(-1, 3))
    m.info = {'source': 'void_cut_body', 'flags': ['void'], 'bodies': len(T), 'tris': len(P) // 3}
    return m, 'mesh'

def wall_openings(ctx, e, org, x0, n, y0, d):
    """cutter boxes for the doors/windows hosted by wall e: the instance's stored bounding box projected into the wall frame (full wall thickness)"""
    from . import occ
    out = []
    for h in ctx.hosted.get(e, []):
        bb = ctx.bbox(h); body = False
        sid = ctx.eid_int(ctx.recs[h]['fields'].get('m_masterSymbolId')); fr_ = inst_frame(ctx, ctx.recs[h]); cp = symbol_cut_points(ctx, sid) if (sid is not None and fr_) else None
        if cp is not None and USE_SYMBOL_CUTS:
            corners = cp @ fr_[0].T + fr_[1]; body = True            # the family's own void body at the instance transform
        elif bb is None: continue
        else: corners = np.array([[x, y, z] for x in (bb[0][0], bb[1][0]) for y in (bb[0][1], bb[1][1]) for z in (bb[0][2], bb[1][2])])
        loc = np.c_[(corners - org) @ x0, (corners - org) @ n, (corners - org) @ y0]
        lo = np.maximum(loc.min(0), 0.0); hi = np.minimum(loc.max(0), d)
        # the instance box is axis aligned in world space; for a wall at an angle it over-covers along the wall: shrink to the box the instance really occupies
        cat_ = ctx.catname(h); sh = OPENING_SHRINK.get(cat_, 0.0) if not body else 0.0       # frames/casing are inside the instance bbox; generic voids are cut as stored
        shz = OPENING_SHRINK_Z.get(cat_, sh) if not body else 0.0
        lo = lo + np.array([sh, 0, shz]); hi = hi - np.array([sh, 0, shz])
        if hi[0] - lo[0] < 0.2 or hi[2] - lo[2] < 0.2: continue
        pad = 0.2
        out.append(occ.box_frame(org + x0 * lo[0] + y0 * lo[2] - n * pad, x0 * (hi[0] - lo[0]), n * (d[1] + 2 * pad), y0 * (hi[2] - lo[2])))
    return out

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
    if c.get('m_NodeArray'):                                                       # Hermite spline (flex ducts / pipes): nodes with parameter, point and tangent dP/dt
        N = c['m_NodeArray']; out = []
        for a_, b_ in zip(N[:-1], N[1:]):
            t0, t1 = float(a_['m_iParametr']), float(b_['m_iParametr']); dt = t1 - t0
            if dt <= 0: continue
            P0, P1 = np.array(a_['m_iPoint'], float), np.array(b_['m_iPoint'], float); T0, T1 = np.array(a_['m_iTangent'], float) * dt, np.array(b_['m_iTangent'], float) * dt
            u = np.linspace(0, 1, 9 if not out else 9)[(1 if out else 0):, None]
            out += list((2 * u ** 3 - 3 * u ** 2 + 1) * P0 + (-2 * u ** 3 + 3 * u ** 2) * P1 + (u ** 3 - 2 * u ** 2 + u) * T0 + (u ** 3 - u ** 2) * T1)
        return np.array(out) if len(out) > 1 else None
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

def group_loops(loops):
    """nesting by containment: even depth = outer boundary, odd depth = hole of its parent. -> [(outer Nx2, [holes])]"""
    from matplotlib.path import Path as _P
    L = [np.asarray(l)[:, :2] for l in loops if len(l) >= 3]
    area = [abs(0.5 * np.sum(l[:, 0] * np.roll(l[:, 1], -1) - np.roll(l[:, 0], -1) * l[:, 1])) for l in L]
    order = sorted(range(len(L)), key=lambda i: -area[i]); paths = {i: _P(L[i]) for i in order}
    parent = {}
    for pos, i in enumerate(order):
        c = L[i].mean(0) if paths[i].contains_point(L[i].mean(0)) else L[i][0]
        pt = L[i][len(L[i]) // 3]
        par = [j for j in order[:pos] if area[j] > area[i] and paths[j].contains_point(pt, radius=-1e-6)]
        parent[i] = par[-1] if par else None
    depth = {}
    for i in order: depth[i] = 0 if parent[i] is None else depth[parent[i]] + 1
    groups = []
    for i in order:
        if depth[i] % 2 == 0: groups.append((L[i], [L[j] for j in order if parent.get(j) == i and area[j] > 1e-6]))
    return groups

def slab_geom(ctx, e, r):
    """floor/ceiling slab: sketch outline (nested loops = outers and holes) extruded between the top and bottom surfaces; sloped planes followed exactly; flat slabs take their stored bbox
    height range when the reference faces do not cover the whole thickness. Layers from the type's compound structure."""
    pls = [p for p in ref_planes(r['fields']) if abs(np.cross(p[1], p[2])[2]) / max(np.linalg.norm(np.cross(p[1], p[2])), 1e-12) > 0.3]
    if len(pls) < 2: return None
    loops = sketch_loops(ctx, e)
    if not loops: return None
    closed = [l for l in loops if len(l) >= 3]
    if not closed: return None
    groups = group_loops(closed)
    if not groups: return None
    big = max(closed, key=lambda l: abs(0.5 * np.sum(l[:, 0] * np.roll(l[:, 1], -1) - np.roll(l[:, 0], -1) * l[:, 1])))
    ctr = big[:, :2].mean(0)[None, :]
    fz = [plane_z(p, ctr) for p in pls]
    zl = float(big[:, 2].mean())      # the sketch plane is also a bounding layer (ceilings hang below their reference faces)
    bbz = ctx.bbox(e)
    if bbz is not None and bbz[0][2] - 1e-3 <= zl <= bbz[1][2] + 1e-3: fz.append(((lambda xy, c=zl: np.full(len(xy), c)), None))
    zc = [f(ctr)[0] for f, _ in fz]
    top = fz[int(np.argmax(zc))][0]; bot = fz[int(np.argmin(zc))][0]
    flat = all(abs(n[2]) > 0.99999 for _, n in fz if n is not None)
    if flat and bbz is not None and (bbz[1][2] - bbz[0][2]) > (max(zc) - min(zc)) + 0.02 and abs(max(zc) - bbz[1][2]) < 0.6:      # reference faces miss the top and/or bottom layer: use Revit's stored extent
        zt, zb = float(bbz[1][2]), float(bbz[0][2]); top = lambda xy, c=zt: np.full(len(xy), c); bot = lambda xy, c=zb: np.full(len(xy), c); zc = zc + [zt, zb]
    if abs(max(zc) - min(zc)) < 1e-6: return None
    layers = type_layers(ctx, type_of(ctx, e, r)); parts = []
    for outer, holes in groups:
        if len(layers) > 1:                  # compound structure: one prism per layer, first layer on top (exterior side of a floor/ceiling)
            tot = sum(L[0] for L in layers); cum = 0.0
            for wd, fn, rgb in layers:
                f0, f1 = cum / tot, (cum + wd) / tot; cum += wd
                lt = (lambda xy, a=f0: top(xy) - a * (top(xy) - bot(xy))); lb = (lambda xy, a=f1: top(xy) - a * (top(xy) - bot(xy)))
                parts.append((geom.prism([outer] + holes, lb, lt), rgb or CORE_GRAY))
        else: parts.append((geom.prism([outer] + holes, bot, top), dominant_rgb(layers)))
    mu = geom.Multi(parts)
    return (mu, 'param') if mu else None

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
    lay = type_layers(ctx, type_of(ctx, e, r)); th = sum(L[0] for L in lay) if lay else None
    return roof_surface(outer, holes, sloped, bb, store=(ctx.roof_fields, e), thick=th)

def roof_surface(outer, holes, sloped, bb, store=None, thick=None):
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
    if thick:                                                    # compound-structure thickness is perpendicular to the slope: vertical thickness = t / cos(slope)
        amax = max(abs(c[1]) for c in sloped); dz = thick / max(np.cos(amax), 0.2)
    if not 0.05 <= dz <= 3.0: dz = float(np.clip(dz, 0.05, 3.0))
    n = len(pts); top = np.c_[pts, zb + dz]; bot = np.c_[pts, zb]
    m = Mesh(np.vstack([top, bot]), np.vstack([tri, tri[:, ::-1] + n]))
    for l in [ring] + hr:                                    # boundary side faces
        k = len(l); idx = [int(np.argmin(np.linalg.norm(pts - q, axis=1))) for q in l]
        for i in range(k):
            a_, b_ = idx[i], idx[(i + 1) % k]
            m.f = np.vstack([m.f, [[a_, b_, b_ + n], [a_, b_ + n, a_ + n]]])
    shift = float(bb[0][2] - m.v[:, 2].min()); m.v[:, 2] += shift          # sketch plane height is only a reference; absolute height comes from the stored bbox
    if store is not None: store[0][store[1]] = (poly, (lambda P, _z=zfun, _s=shift, _d=dz: _z(P) + _s + _d * ROOF_ATTACH_FRACTION))
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

def record_curves(fields):
    """every stored line / arc node of a record (m_origin + m_dirVec + m_endParams, or m_center + m_radius + m_xVec/m_yVec + m_endParams) -> list of point arrays"""
    out = []
    def walk(n):
        if isinstance(n, list):
            for x in n: walk(x)
            return
        if not isinstance(n, dict): return
        n = n.get('obj', n)
        if not isinstance(n, dict): return
        try:
            if 'm_endParams' in n and 'm_dirVec' in n and 'm_origin' in n:
                o = np.array(n['m_origin'], float); d = np.array(n['m_dirVec'], float); t0, t1 = n['m_endParams'][:2]; out.append(np.array([o + d * t0, o + d * t1])); return
            if 'm_endParams' in n and 'm_radius' in n and 'm_center' in n:
                c = np.array(n['m_center'], float); x = np.array(n['m_xVec'], float); y = np.array(n['m_yVec'], float); rr = float(n['m_radius']); t0, t1 = n['m_endParams'][:2]
                t = np.linspace(t0, t1, max(3, int(abs(t1 - t0) / 0.1) + 2)); out.append(c + rr * np.cos(t)[:, None] * x + rr * np.sin(t)[:, None] * y); return
        except Exception: return
        for v in n.values():
            if isinstance(v, (dict, list)): walk(v)
    walk(fields)
    seen = set(); res = []
    for p in out:
        k = tuple(np.round(p[[0, -1]], 5).ravel()); k2 = tuple(np.round(p[[-1, 0]], 5).ravel())
        if k in seen or k2 in seen or np.linalg.norm(p[-1] - p[0]) < 1e-9 and len(p) == 2: continue
        seen.add(k); res.append(p)
    return res

class SegSet(LineSet):
    """several polylines as one set of GL line segments"""
    def __init__(self, polys):
        vs = []; fs = []; n = 0
        for p in polys:
            p = np.asarray(p, float); vs.append(p); fs.append(np.c_[np.arange(len(p) - 1), np.arange(1, len(p))] + n); n += len(p)
        self.v = np.vstack(vs) if vs else np.zeros((0, 3)); self.f = (np.vstack(fs) if fs else np.zeros((0, 2))).astype(np.int32)

def curve_lines_geom(ctx, e, r):
    """2D-ish datum elements (property lines and their segments): the stored curves as lines, never a box"""
    polys = record_curves(r['fields'])
    return (SegSet(polys), 'line') if polys else None

def rebar_geom(ctx, e, r):
    """reinforcement bars from the rebar shape definition (reader rvt_rebar: centre lines swept with the bar diameter; exact vs Revit on the 2020 samples)"""
    try:
        reader._import(); import rvt_rebar as RR
        T = RR.rebar_mesh(ctx.src, int(e))
    except Exception as ex: ctx._why[e] = 'rebar: %r' % ex; return None
    if T is None or not len(T): return None
    P = np.asarray(T, float).reshape(-1, 3); m = Mesh(P, np.arange(len(P)).reshape(-1, 3))
    m.info = {'source': 'rebar shape definition (centre lines + bar diameter, reader rvt_rebar)', 'flags': [], 'bodies': 1, 'tris': len(P) // 3}
    return m, 'mesh'

def grid_line_geom(ctx, e, r):
    """curtain grid line: the full (host-wide) line stored in m_pFullCurve (a line in the curtain wall's plane)"""
    pts = curve_pts(g(r['fields'], 'm_pFullCurve'))
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
BUILDERS = {'Rebar': rebar_geom, 'RebarInSystem': rebar_geom, 'LineLoad': line_geom, 'Property': curve_lines_geom, 'PropertyLineSegment': curve_lines_geom, 'ArcWall': wall_geom, 'ProfileRoof': roof_geom, 'FootPrintRoof': roof_geom, 'SWall': wall_geom, 'Floor': slab_geom, 'Ceiling': slab_geom, 'RoofSoffit': slab_geom, 'BuildingPad': slab_geom, 'RbsDuctCurve': mep_geom, 'RbsPipeCurve': mep_geom, 'RbsConduitCurve': mep_geom, 'CableTray': mep_geom,
            'RbsFlexDuctCurve': mep_geom, 'RbsFlexPipeCurve': mep_geom, 'CurveElem': line_geom, 'CurtainGridLine': grid_line_geom, 'FamilyInstance': instance_box}
HIDE_DEFAULT_CATS = {'Structural Rebar', 'Spaces', 'HVAC Zones', 'Center line', '<Sketch>', 'Work Plane Grid', 'Cameras', 'Scope Boxes', 'Boundary Conditions', 'Area Loads', 'Line Loads', 'Point Loads', 'Division Profiles',
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
    if r['class'].startswith(('DBView', 'Analytical')) or ctx.bbox(e) is None: return None
    gs = [x for x in brep.find_geometries(r['fields']) if len(x['m_pFaces']) >= 4]
    if not gs: return None
    m = Mesh(); npl = 0; nsk = 0
    for gm in gs:
        comps = brep.reader_components(gm)               # the reader's shell split (rvt_mesh.components) when available: only closed shells count as solid
        if comps is not None:
            for c in comps:
                if c['tris'] and c.get('closed') and not c['unsupported']:
                    P = np.array(c['tris'], float).reshape(-1, 3); m.add(Mesh(P, np.arange(len(P)).reshape(-1, 3))); npl += c['n_faces']
                else: nsk += 1
            continue
        mm, n, sk = brep.geometry_mesh(gm); m.add(mm); npl += n; nsk += sk
    if not m: return None
    bb = ctx.bbox(e)
    if bb is not None and box_iou(m.v.min(0), m.v.max(0), *bb) < 0.5: return None
    return m, ('solid' if nsk == 0 else 'partial')

def contained_match(lo, hi, blo, bhi, tol=0.15):
    """our mesh lies inside Revit's stored bbox (which also covers hosted sweeps/attachments) and spans >= 93% of its two largest dimensions"""
    if np.any(lo < blo - tol) or np.any(hi > bhi + tol): return False
    rd = bhi - blo; od = hi - lo; big = np.argsort(rd)[::-1][:2]
    return bool(np.all(od[big] >= 0.93 * rd[big] - 1e-6))

ANALYTIC_CLASSES = {'ArcWall', 'SWall', 'Floor', 'Ceiling', 'RoofSoffit', 'BuildingPad', 'ProfileRoof', 'FootPrintRoof', 'RbsDuctCurve', 'RbsPipeCurve', 'RbsConduitCurve', 'CableTray', 'RbsFlexDuctCurve', 'RbsFlexPipeCurve', 'CurveElem'}
USE_READER_MESH = True

def reader_brep_extra(ctx, e, GG):
    try:
        from . import occsurf
        b = GG.element_brep(ctx.src, e)
        faces = [f for f in b.get('faces', []) if f['surface'].get('type') not in ('plane', 'cylinder') and f.get('loops_uv')]
        if not faces: return None
        out = Mesh(); types = collections.Counter()
        for f in faces:
            try: out.add(occsurf.tessellate_face(f['surface'], f['loops_uv'])); types[f['surface']['type']] += 1
            except Exception: continue
        out.face_types = dict(types)
        if not out: return None
        inst = b.get('instances') or []
        if inst:  # (kept: pick the frame that lands inside the stored bbox)
            tr = inst[0]['transform']; M = np.array(tr['m_3x3'], float); o = np.array(tr['m_or'], float); bb = ctx.bbox(e)
            if bb is not None:
                cands = [out.v, out.v @ M.T + o, out.v @ M + o]                  # top-level faces are in world coordinates, instance faces in the symbol frame
                fit = lambda W: float(np.mean(np.all((W >= bb[0] - 0.5) & (W <= bb[1] + 0.5), axis=1)))
                out.v = max(cands, key=fit)
        return out
    except Exception:
        return None

MESH_FIRST = {'SWall', 'ArcWall', 'Floor', 'Ceiling', 'ProfileRoof', 'FootPrintRoof', 'RoofSoffit', 'BuildingPad', 'RbsDuctCurve', 'RbsPipeCurve', 'RbsConduitCurve', 'CableTray', 'RbsFlexDuctCurve', 'RbsFlexPipeCurve'}      # saved-graphics meshes match Revit volumes within 2% far more often than the parametric rebuilds (2020 residential walls 92% vs 57%, roofs 100% vs 0%)

_GUARD_GB = [2.5]

def _guarded(fn, *a, extra_gb=None):
    """call fn with the address space capped at (current + extra_gb): a runaway reader decode of one element raises MemoryError (-> None) instead of getting the whole process OOM-killed"""
    import resource
    extra_gb = _GUARD_GB[0] if extra_gb is None else extra_gb
    cur = int(open('/proc/self/statm').read().split()[0]) * resource.getpagesize(); old = resource.getrlimit(resource.RLIMIT_AS)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (cur + int(extra_gb * 2 ** 30), old[1]))
        return fn(*a)
    except MemoryError: return None
    finally:
        resource.setrlimit(resource.RLIMIT_AS, old)

CURVED_SURFACES = {'revolution', 'cone', 'sphere', 'torus'}      # analytic curved faces only; the check is expensive (refined_volume ~10 s for big meshes), so only meshes up to 1500 triangles, time-boxed to 3 s

_RUST_ISSUES = {}
def _note_rust_issue(what, ex):
    k = (what, repr(ex)[:120])
    if k not in _RUST_ISSUES: _RUST_ISSUES[k] = 1; print('Rust fast path %s failed (%r): Python reference used' % (what, ex), flush=True)

def _dump_refined_fail(a, ex):
    """the reference rvt_mesh.refined_volume raised (c5-geometry cannot reproduce it from element_mesh): keep its exact arguments for them, ~/rvt-research/ana_c5/ri_fail_<eid>.pkl (max 20 files), and print the traceback"""
    import traceback, pickle
    traceback.print_exc()
    try:
        d = os.path.expanduser('~/rvt-research/ana_c5'); os.makedirs(d, exist_ok=True)
        eid = a.get('eid', a.get('id', a.get('nid', 'x')))
        if len([f for f in os.listdir(d) if f.startswith('ri_fail_')]) < 20:
            pickle.dump({'tris_raw': a.get('tris_raw'), 'meta_raw': a.get('meta_raw'), 'fid': a.get('fid'), 'keys': sorted(a), 'error': repr(ex), 'tb': traceback.format_exc()}, open(os.path.join(d, 'ri_fail_%s.pkl' % eid), 'wb'))
            print('refined_volume failure arguments saved to', d, flush=True)
    except Exception as ex3_: print('refined_volume failure arguments NOT saved:', repr(ex3_), flush=True)

def topology_check(a, P):
    """the reader validates curved solids with analytic (refined) volume/area; compare the triangle mesh's own area with it: a mesh whose triangles span the wrong vertices has the right volume on paper but draws wrongly. -> (ok, mesh_area, analytic_area) or None"""
    if not a.get('tris_raw') or not a.get('meta_raw'): return None
    try:
        import rvt_mesh as RM
        import signal
        def _to(sig, frm): raise TimeoutError()
        old = signal.signal(signal.SIGALRM, _to); signal.setitimer(signal.ITIMER_REAL, 3.0)
        VF = fast_module(); rv = getattr(VF, 'refined_volume', None) if VF is not None else None          # Rust drop-in (same result to 1e-9, ~50x faster) when available
        try:
            try: v_, closed, area_ref = (rv or RM.refined_volume)(a['tris_raw'], a['meta_raw'], fid=a.get('fid'))[:3]
            except (KeyboardInterrupt, SystemExit, TimeoutError): raise
            except BaseException as ex_:                       # a Rust panic (pyo3 PanicException is a BaseException): the Python reference instead
                if rv is None: raise
                _note_rust_issue('refined_volume', ex_)
                try: v_, closed, area_ref = RM.refined_volume(a['tris_raw'], a['meta_raw'], fid=a.get('fid'))[:3]
                except Exception as ex2_: _dump_refined_fail(a, ex2_); raise
        finally: signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)
        T = P.reshape(-1, 3, 3); area = float(np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1).sum() / 2)
        return ((0.6 <= area / area_ref <= 1.5) if area_ref > 1e-9 else True), area, float(area_ref)      # tolerance is wide on purpose: the analytic area omits some caps (duct fittings read 1.1-1.3 with correct meshes); the torus reads 1.6, facade members up to 3.3
    except Exception: return None

def _doc(GG, src):
    """the reader's element-mesh document for src, shared with rvt_geometry (GG._docs): the Rust-backed rvt_fast.Doc (same results, records from Rust buffers + symbol memo) when it works, else rvt_elemmesh.Doc"""
    d = GG._docs.get(src)
    if d is not None: return d
    import rvt_elemmesh as EM
    if os.environ.get('RVT_FASTDOC', '1') != '0' and not os.environ.get('RVT_NOFAST'):          # default since rvt-core fixed the fork deadlock (2026-10-13); RVT_FASTDOC=0 selects the Python Doc
        try:
            sys.path.append(os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as F
            if F.on(): d = F.Doc(src)
        except Exception as ex: print('rvt_fast.Doc unavailable (%r): using the Python reader' % ex)
    if d is None: d = EM.Doc(src)
    GG._docs[src] = d; return d

def _em_geometry(GG, src, e):
    """rvt_elemmesh.element_mesh result in the element_geometry vocabulary (one triangle_mesh solid) plus the per-triangle body (nid) and face (fid) ids"""
    import rvt_elemmesh as EM
    d = _doc(GG, src)                                            # (the document build uses worker pools: never under the address-space guard)
    m = _guarded(EM.element_mesh, d, int(e))
    if not m: return {'confidence': 'none', 'flags': ['decode_failed_or_over_memory_guard']}
    if not m['tris']: return {'confidence': 'none', 'flags': list(m.get('flags') or []) or ['no_saved_graphics']}
    P = np.array([p for t in m['tris'] for p in t])
    mt = m.get('meta') or []
    return {'confidence': 'mesh_approx', 'flags': ['saved_graphics_tessellation'] + list(m['flags']), 'nid': list(m.get('nid') or []), 'fid': list(m.get('fid') or []),
            'mat': [int(x) if x is not None else -1 for x in m['mat']] if m.get('mat') is not None and len(m['mat']) == len(m['tris']) else None,
            'surf': [str(x[0]) for x in mt] if len(mt) == len(m['tris']) else None, 'tris_raw': m['tris'] if (len(m['tris']) <= 1500 and any(str(x[0]) in CURVED_SURFACES for x in mt)) else None, 'meta_raw': mt if (len(m['tris']) <= 1500 and any(str(x[0]) in CURVED_SURFACES for x in mt)) else None,
            'solids': [{'kind': 'triangle_mesh', 'triangles': P.round(6).tolist(), 'source': m['source']}]}

def _body_summary_fast(P, nid, fid, surf):
    """Rust body_summary (identical output) when available; any failure (incl. a Rust panic) uses the Python version"""
    VF = fast_module(); bs = getattr(VF, 'body_summary', None) if VF is not None else None
    if bs is not None:
        try: return bs(P, nid, fid, surf)
        except (KeyboardInterrupt, SystemExit): raise
        except BaseException as ex: _note_rust_issue('body_summary', ex)
    return body_summary(P, nid, fid, surf)

def body_summary(P, nid, fid=None, surf=None, limit=12):
    """per body of an element's saved-graphics mesh (nid = body id per triangle): triangles, faces (fid), area (ft2), watertight; kind from the id range (polymesh 1e6, symbol instance >= 2e7).
    Vertex welding and edge counting are done once for the whole element (one sort), then split per body."""
    nid = np.asarray(nid); T = P.reshape(-1, 3, 3); out = []
    cr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ta = np.linalg.norm(cr, axis=1) / 2
    keys = np.round(T.reshape(-1, 3) * 1e4).astype(np.int64); _, inv = np.unique(keys, axis=0, return_inverse=True); inv = inv.reshape(-1, 3)
    bodies = sorted(set(nid.tolist()))[:limit]; bidx = {b: k for k, b in enumerate(bodies)}
    tb = np.array([bidx.get(x, -1) for x in nid.tolist()]); E = np.sort(np.concatenate([inv[:, [0, 1]], inv[:, [1, 2]], inv[:, [2, 0]]]), axis=1); eb = np.tile(tb, 3)
    ok = eb >= 0; ek = np.c_[eb[ok], E[ok]]; uk, cnt = np.unique(ek, axis=0, return_counts=True); odd = np.zeros(len(bodies), bool)
    if len(uk): np.logical_or.at(odd, uk[:, 0], cnt % 2 == 1)
    fida = np.asarray(fid) if fid is not None and len(fid) == len(nid) else None; surfa = np.asarray(surf, dtype=object) if surf is not None and len(surf) == len(nid) else None
    for k, b in enumerate(bodies):
        ix = np.nonzero(tb == k)[0]; t = T[ix]; area = float(ta[ix].sum())
        closed = 'yes' if not odd[k] else ('sealed' if float(np.linalg.norm(cr[ix].sum(0))) < 1e-4 * max(area, 1e-9) else 'open')
        out.append({'id': int(b), 'kind': 'polymesh' if b == 10 ** 6 else ('symbol instance' if b >= 2 * 10 ** 7 else 'own geometry'), 'tris': int(len(ix)), 'faces': int(len(set(fida[ix].tolist()))) if fida is not None else None,
                    'surfaces': dict(collections.Counter(surfa[ix].tolist())) if surfa is not None else None, 'area': round(area, 3), 'closed': closed, 'lo': t.reshape(-1, 3).min(0).round(3).tolist(), 'hi': t.reshape(-1, 3).max(0).round(3).tolist()})
    return out

_GST = {}
_SYM_NM = {}

def body_materials(GG, src, e):
    """{nid: Revit material id}: the material of each saved-graphics body = graphics style of the Geometry node's category (own nodes: nid = node index; symbol instances: nid = 2e7 + k*1e5 + node index of the k-th drawn symbol)"""
    import rvt_elemmesh as EM, rvt_materials as RM
    d = _doc(GG, src); rec = d.rec(int(e))
    if rec is None: return {}
    def nodes(fl):
        g_, i_ = EM._geos_f(fl, 3)
        if not g_ and not i_: g_, i_ = EM._geos(fl)
        return g_, i_
    def node_mats(geos):
        out = []
        for g_ in geos:
            cat = RM._eid((g_.get('m_GInfo') or {}).get('m_categoryId'))
            if cat is None: out.append(None); continue
            if (src, cat) not in _GST: _GST[(src, cat)] = RM.gstyle_material(src, cat)
            out.append(_GST[(src, cat)])
        return out
    geos, inst = nodes(rec['fields']); mp = {i: m for i, m in enumerate(node_mats(geos)) if m is not None}
    inst = [z for z in inst if not (isinstance(z.get('m_forbiddenTarget'), dict) and z['m_forbiddenTarget'].get('m_targets'))] or inst
    inst = [z for z in inst if d.cls(EM._ob(z['m_instanceInfo']).get('m_symbolId')) != 'FamilyInstance']
    k = 0
    for z in inst:
        ii = EM._ob(z['m_instanceInfo']); sid = ii.get('m_symbolId')
        if not ii.get('m_Trf') or sid is None: continue
        key = (src, int(sid))
        if key not in _SYM_NM:                                  # symbols repeat across instances: their node materials once per symbol
            sr = d.rec(int(sid)); sg = nodes(sr['fields'])[0] if sr is not None else []
            _SYM_NM[key] = node_mats(sg) if sg else None
        if not _SYM_NM[key]: continue
        k += 1
        for gi, m in enumerate(_SYM_NM[key]):
            if m is not None: mp[2 * 10 ** 7 + k * 100000 + gi] = m
    return mp


def dominant_layer_material(ctx, tid):
    """Revit id of the material of the widest compound-structure layer that has one (walls, floors, roofs, ceilings)"""
    r = ctx.recs.get(tid) if tid is not None else None
    cs = g(r['fields'], 'm_pCompoundStructure') if r else None
    best = None
    for L in (cs or {}).get('m_layers') or []:
        w = float(L.get('m_layerWidth') or 0); mid = ctx.eid_int(L.get('m_materialId'))
        if w > 1e-6 and mid in ((getattr(ctx, 'mats', None) or {}).get('index') or {}) and (best is None or w > best[0]): best = (w, mid)
    return best[1] if best else None


def param_material(ctx, e, r):
    """material named by an element/type parameter (Material, Structural Material, Finish, Glass, ...) -> Revit material id or None"""
    from . import materials as MT
    idx = (getattr(ctx, 'mats', None) or {}).get('index') or {}
    for src_id in (e, type_of(ctx, e, r)):
        p = ctx.par.get(src_id, {}).get('params', {}) if src_id is not None else {}
        for k in MT.MATERIAL_PARAMS:
            v = p.get(k)
            if isinstance(v, int) and not isinstance(v, bool):
                v = ctx.eid_int(v) if v >= (1 << (8 * ctx.W - 1)) else v
                if v in idx: return v
    for src_id in (e, type_of(ctx, e, r)):                    # unnamed built-in ElementId parameters stored on the record (e.g. a toposurface's material): any value that is a Material
        rr = r if src_id == e else (ctx.recs.get(src_id) if src_id is not None else None)
        pv = (rr or {}).get('fields', {}).get('m_pParamValueSetElementId') if rr else None
        pv = pv.get('obj', pv) if isinstance(pv, dict) else None
        for it in ((pv or {}).get('m_paramSet') or []):
            v = ctx.eid_int(it.get('m_value')) if isinstance(it, dict) else None
            if v in idx: return v
    return None


def _split_by_material(m, nid, ntri0, mp, idx, tri_mat=None):
    """-> geom.Multi of per-material sub-meshes (each .mat = position in the material list), or the mesh itself with .mat set when one material covers it; None when no body has a material.
    tri_mat: Revit material id per reader triangle (-1 = unassigned); bodies' materials (mp: nid -> material id) fill the unassigned ones"""
    import numpy as _np
    if (not mp and tri_mat is None) or not idx: return None
    tm = _np.full(len(m.f), -1, int); nid = _np.asarray(nid)
    for b, mid in (mp or {}).items():
        if mid in idx: tm[:ntri0][nid == b] = idx[mid]
    if tri_mat is not None:
        tv = _np.array([idx.get(int(x), -1) for x in tri_mat], int)[:ntri0]; tm[:len(tv)] = _np.where(tv >= 0, tv, tm[:len(tv)])
    if ntri0 < len(m.f):                                    # extra B-rep faces (no body id): take the most common material
        known = tm[:ntri0][tm[:ntri0] >= 0]
        tm[ntri0:] = _np.bincount(known).argmax() if len(known) else -1
    if (tm < 0).all(): return None
    kinds = sorted(set(tm.tolist()))
    if len(kinds) == 1 and kinds[0] >= 0: m.mat = kinds[0]; return m
    parts = []
    for k in kinds:
        f_ = m.f[tm == k]; used, inv = _np.unique(f_, return_inverse=True); sub = Mesh(m.v[used], inv.reshape(-1, 3)); sub.mat = k if k >= 0 else None; parts.append((sub, None))
    mu = geom.Multi(parts); mu.info = getattr(m, 'info', None); return mu


def reader_mesh(ctx, e, a_pre=None):
    """triangle mesh the reader decoded from Revit's saved graphics (rvt_geometry.element_geometry, confidence 'mesh_approx', world feet): the family-instance geometry. -> (Mesh, fid) or None"""
    if not USE_READER_MESH or not getattr(ctx, 'src', None): return None
    if getattr(ctx, '_rm', None) is not None: return ctx._rm.get(e)          # prefetched in the parent process (workers must not each load the reader's geometry context)
    try:
        reader._import(); import rvt_geometry as GG
        cl = ctx.recs[e]['class']
        a = None; b_ = GG.BUILDERS.get(cl)
        if b_ is not None and cl not in MESH_FIRST:                  # the reader's analytic builder answers first for its classes (as in element_geometry)
            gc_ = GG.get_ctx(ctx.src); rec_ = gc_.rec(e)
            try: a = b_(gc_, int(e), rec_) if rec_ is not None else None
            except Exception: a = None
            if a is not None and a.get('confidence') == 'box': a = None
        if a is None: a = a_pre if a_pre is not None else (_em_geometry(GG, ctx.src, e) or {})          # straight from the reader's element_mesh (or the Rust stream): keeps the per-body (nid) / per-face (fid) ids
    except Exception as ex_:
        ctx._why[e] = 'reader error: %r' % ex_; return None
    if a.get('confidence') != 'mesh_approx':
        ctx._why[e] = 'reader: %s%s' % (a.get('confidence') or 'none', (' (' + ', '.join(a.get('flags') or []) + ')') if a.get('flags') else ''); return None
    T = [np.array(sl['triangles'], float).reshape(-1, 3) for sl in a['solids'] if sl.get('kind') == 'triangle_mesh' and sl.get('triangles')]
    if not T: return None
    P = np.vstack(T)
    if a.get('nid') is not None and len(a['nid']) == len(P) // 3 and len(set(a['nid'])) > 1:      # coincident duplicate bodies (e.g. duct lining on the duct surface): keep the first, they z-fight
        nid = np.asarray(a['nid']); TT = P.reshape(-1, 3, 3); seen = {}; drop = set()
        for b in dict.fromkeys(nid.tolist()):
            t = TT[nid == b]; k = (len(t), tuple(np.round(t.reshape(-1, 3).min(0), 3)), tuple(np.round(t.reshape(-1, 3).max(0), 3)))
            if k in seen: drop.add(b)
            else: seen[k] = b
        if drop:
            keep = ~np.isin(nid, list(drop)); P = TT[keep].reshape(-1, 3)
            a = dict(a, **{k_: [x for x, kp in zip(a[k_], keep) if kp] for k_ in ('nid', 'fid', 'mat', 'surf') if a.get(k_) is not None and len(a[k_]) == len(keep)})
            a['flags'] = list(a.get('flags') or []) + ['duplicate_bodies_dropped']
            if os.environ.get('RVT_RI_SKIP_DEDUPED', '1') != '0': a['tris_raw'] = a['meta_raw'] = None      # fid was filtered above, tris_raw / meta_raw were not: refined_volume got arguments of different lengths (IndexError in the reference on 2017 rme_advanced); the topology check is skipped for these elements
    m = Mesh(P, np.arange(len(P)).reshape(-1, 3))
    m.info = {'source': next((sl.get('source') for sl in a['solids'] if sl.get('source')), None), 'flags': list(a.get('flags') or []), 'bodies': len(a['solids']), 'tris': len(P) // 3}
    if a.get('nid') is not None and len(a['nid']) == len(P) // 3: m.info['body_list'] = _body_summary_fast(P, a['nid'], a.get('fid'), a.get('surf')); m.info['bodies'] = len(set(a['nid']))
    tc = topology_check(a, P)
    if tc is not None:
        m.info['mesh_area'] = round(tc[1], 3); m.info['analytic_area'] = round(tc[2], 3)
        if not tc[0]: m.info['flags'] = m.info['flags'] + ['mesh_topology_suspect']
    if a.get('surf') is not None: m.info['surfaces'] = dict(collections.Counter(a['surf']))               # triangles per source surface type (plane, cylinder, cone, sphere, torus, revolution, ruled, hermite, bspline ...)
    bb = ctx.bbox(e); extra = False
    if 'unsupported_faces' in (a.get('flags') or []):
        ex = reader_brep_extra(ctx, e, GG)                       # faces the saved-graphics mesh skipped (cone / revolution / ruled / Hermite ...): tessellated through OpenCascade
        if ex is not None and len(ex.f): m.add(ex); P = m.v; extra = True; m.info['extra_faces'] = getattr(ex, 'face_types', None); m.info['surfaces'] = {**m.info.get('surfaces', {}), **{'%s (OpenCascade)' % k: v for k, v in (getattr(ex, 'face_types', None) or {}).items()}}
    iou = box_iou(P.min(0), P.max(0), *bb) if bb is not None else 1.0
    inside = bb is None or (bool(np.all(P.min(0) >= bb[0] - 0.3)) and bool(np.all(P.max(0) <= bb[1] + 0.3)))      # the stored element bbox also covers swings / clearances: a mesh inside it is the element's own geometry
    if ctx.recs[e]['class'] in MESH_FIRST and iou < 0.6: ctx._why[e] = 'saved graphics disagree with the stored box (IoU %.2f)' % iou; return None      # host elements: the saved graphics must match the stored box (curtain walls etc. fall back to the parametric builder)
    if iou < 0.4 and not inside: ctx._why[e] = 'saved graphics are not this element\'s own geometry (IoU %.2f, outside box)' % iou; return None                    # neither matching nor contained: not the element's own geometry
    fidv = ('approx' if 'mesh_topology_suspect' in m.info['flags'] else ('approx' if ('unsupported_faces' in (a.get('flags') or []) and not extra) or (iou < 0.9 and not inside) else 'mesh'))
    if fidv == 'approx' and 'mesh_topology_suspect' in m.info['flags']: ctx._why[e] = 'reader mesh area %.1f ft2 vs analytic %.1f ft2: triangles do not follow the surface' % (m.info['mesh_area'], m.info['analytic_area'])
    mats = getattr(ctx, 'mats', None)
    if mats and mats['list']:
        try:
            tri_mat = a.get('mat') if a.get('mat') is not None and len(a['mat']) == len(P) // 3 else None       # per-triangle material from the reader (face render style first): beats the per-body guess
            full = tri_mat is not None and len(tri_mat) and int(np.min(tri_mat)) >= 0 and a.get('nid') is not None and len(a['nid']) == len(tri_mat)
            if full:                                             # every triangle has a material: the per-body map would change nothing (c2-rust, 5 files, 0 triangles), derive it from the triangles (~1.4 s saved on Structural)
                nid_ = np.asarray(a['nid']); tm_ = np.asarray(tri_mat, np.int64); mp = {}
                for b_ in np.unique(nid_):
                    v_, c_ = np.unique(tm_[nid_ == b_], return_counts=True); mp[int(b_)] = int(v_[c_.argmax()])
            else: mp = body_materials(GG, ctx.src, e) if a.get('nid') is not None else {}
            if tri_mat is not None: m.info['material_source'] = 'per face (reader)'
            elif mp: m.info['material_source'] = 'per body (graphics style of the geometry node)'
            res = _split_by_material(m, a.get('nid'), len(a['nid']) if a.get('nid') is not None else 0, mp, mats['index'], tri_mat) if (mp or tri_mat is not None) else None
            if res is not None:
                m = res
                for bi in (m.info or {}).get('body_list') or []:
                    if bi['id'] in mp and mp[bi['id']] in mats['index']: bi['material'] = mats['index'][mp[bi['id']]]
        except Exception as ex_: ctx._why.setdefault(e, 'materials: %r' % ex_)
    return m, fidv

_PF = {}

def _rf():
    """the rvt_fast module (Rust kernels: smooth_part, file_key, ...) when the fast path is on, else None"""
    return sys.modules.get('rvt_fast') if fast_module() is not None else None

def fast_module():
    """~/src/rvt-core/python/rvt_viewer_fast (Rust fast paths: element table in ~1 s, streamed meshes, progress file) or None (RVT_NOFAST=1, missing extension, import error)"""
    if os.environ.get('RVT_NOFAST'): return None
    try:
        sys.path.insert(0, os.path.expanduser('~/src/rvt-core/python')); sys.path.insert(0, reader.READER_DIR)
        import rvt_fast as RF
        if not RF.on(): return None
        import rvt_viewer_fast as VF; return VF
    except Exception as ex:
        print('Rust fast path unavailable (%r): using the Python reader' % ex); return None

def _prefetch_chunk(ids):
    ctx = _PF['ctx']; out = []
    for e in ids:
        try: r = reader_mesh(ctx, e)
        except Exception: r = None
        out.append((e, r, ctx._why.get(e)))
    return out

def _mesh_workers():
    """forked mesh workers: <= 6, bounded by the cgroup memory limit minus what the parent already holds (each worker grows by up to ~1 GB on big files)"""
    n = max(1, min(6, (os.cpu_count() or 2) - 1))
    try:
        cg = open('/proc/self/cgroup').read().strip().split('::')[-1]; lim = open('/sys/fs/cgroup%s/memory.max' % cg).read().strip()
        rss = int(open('/proc/self/statm').read().split()[1]) * 4096 / 2 ** 30
        if lim != 'max': n = max(1, min(n, int((int(lim) / 2 ** 30 - rss - 0.7) / 1.0)))
    except Exception: pass
    return int(os.environ.get('RVT_WORKERS', n))

def _stream_has_materials(fm, todo):
    """does the Rust mesh stream return the per-triangle material ('mat') the Python element_mesh returns? (probe a few elements)"""
    try:
        VF = fast_module(); seen = 0
        for e, a in VF.em_geometries(fm, todo[:6]):
            if a.get('confidence') == 'mesh_approx':
                if a.get('mat') is not None: return True
                seen += 1
        return seen == 0
    except BaseException: return False

def prefetch_reader_meshes(ctx, els, prog=None, on_partial=None):
    """saved-graphics meshes of every element that takes them, decoded in forked workers (the reader document is built once in the parent and shared copy-on-write); partial results stream into the progressive display"""
    ctx._rm = None; out = {}; n = 0; last_p = time.time(); idx = {el['id']: i for i, el in enumerate(els)}
    todo = [el['id'] for el in els if not (not el['cat'] or el['isType'] or (ctx.recs[el['id']]['class'] in ANALYTIC_CLASSES and ctx.recs[el['id']]['class'] not in MESH_FIRST) or (ctx.bbox(el['id']) is None and el['id'] in ctx.eh and ctx.recs[el['id']]['class'] not in MESH_FIRST))]
    total = len(todo); nw = _mesh_workers(); pf = float(os.environ.get('RVT_PARTIAL_SECS', '12'))
    def account(e, r):
        nonlocal n, last_p
        out[e] = r; n += 1
        if on_partial and n < total and time.time() - last_p > pf:
            on_partial([(idx[e_], r_[1], 'tri', [(r_[0].v, r_[0].f, None)] if not isinstance(r_[0], geom.Multi) else [(pm.v, pm.f, rgb, getattr(pm, 'mat', None)) for pm, rgb in r_[0].parts], getattr(r_[0], 'info', None)) for e_, r_ in out.items() if r_ is not None], n, total); last_p = time.time()
        if prog and (n % 40 == 0 or n == total): prog.set('geometry', 0.4 * n / max(1, total), 'reading saved-graphics meshes %d/%d%s' % (n, total, ' (%d workers)' % nw if nw > 1 else ''), done=n, total=total, sub='Reading saved graphics (decoding meshes)')
    fm = getattr(ctx, 'fm', None)
    if os.environ.get('RVT_NOSTREAM'): fm = None                  # test switch: the forked-worker path on the shared document
    if fm is not None and todo and not _stream_has_materials(fm, todo) and os.path.getsize(ctx.src) <= float(os.environ.get('RVT_MAT_PY_MB', '25')) * 1e6:
        print('the Rust mesh stream has no per-face materials yet: Python meshes for this file (<= %s MB)' % os.environ.get('RVT_MAT_PY_MB', '25')); fm = None      # interim, until rvt-core mirrors element_mesh 'mat'
    if fm is not None and todo:                              # Rust streaming meshes (parallel, results as they finish); analytic-builder classes still go through reader_mesh
        try:
            VF = fast_module(); stream = VF.em_geometries(fm, todo)
            for e, a in stream:
                try: r = reader_mesh(ctx, e, a_pre=a)
                except Exception: r = None
                if ctx._why.get(e) is None and r is None and a.get('confidence') != 'mesh_approx': ctx._why[e] = 'reader: %s (%s)' % (a.get('confidence'), ', '.join(a.get('flags') or []))
                account(e, r)
            ctx._rm = out; return
        except (KeyboardInterrupt, SystemExit): raise
        except BaseException as ex:                            # incl. Rust panics
            print('streaming meshes failed (%r): falling back to the Python reader' % ex); out.clear(); n = 0
    if todo:
        try: reader_mesh(ctx, todo[0])                       # builds the shared reader context (document, census, materials) in the parent before forking
        except Exception: pass
    if nw <= 1 or total < 80:
        for e in todo:
            try: account(e, reader_mesh(ctx, e))
            except Exception: account(e, None)
    else:
        import multiprocessing as mp
        try:                                                  # per-worker address-space allowance so that nw workers together stay inside the memory cap
            cg = open('/proc/self/cgroup').read().strip().split('::')[-1]; lim = open('/sys/fs/cgroup%s/memory.max' % cg).read().strip()
            if lim != 'max': _GUARD_GB[0] = max(0.6, min(2.5, (int(lim) / 2 ** 30 - int(open('/proc/self/statm').read().split()[1]) * 4096 / 2 ** 30 - 0.7) / nw * 0.8))
        except Exception: pass
        _PF['ctx'] = ctx; chunk = 12; parts = [todo[k:k + chunk] for k in range(0, total, chunk)]
        with mp.get_context('fork').Pool(nw) as pool:
            for res in pool.imap_unordered(_prefetch_chunk, parts):
                for e, r, why in res:
                    if why: ctx._why[e] = why
                    account(e, r)
    ctx._rm = out

CONTAINER_CLASSES = {'JoistSystem', 'BeamSystem', 'ElementGroup', 'GStyleElem', 'RebarSystem', 'CategoryElem'}          # layout containers: zero-height bbox, no graphics of their own (the members are separate FamilyInstances); CategoryElem = Revit's category object (2020 Residential: id 229 'Walls' carries a foundation wall's bbox, its box z-fought the wall)

LAYERED_CLASSES = {'SWall', 'ArcWall', 'Floor', 'Ceiling', 'ProfileRoof', 'FootPrintRoof', 'RoofSoffit', 'BuildingPad'}

def element_mesh(ctx, e, r):
    res = _element_mesh(ctx, e, r)
    mats = getattr(ctx, 'mats', None)
    if res is not None and mats and mats['list'] and getattr(res[0], 'kind', 'tri') == 'tri' and not isinstance(res[0], geom.Multi) and getattr(res[0], 'mat', None) is None:
        try:
            mid = dominant_layer_material(ctx, type_of(ctx, e, r)) if r['class'] in LAYERED_CLASSES else param_material(ctx, e, r)
            if mid in mats['index']: res[0].mat = mats['index'][mid]
        except Exception: pass
    if res is not None and getattr(res[0], 'info', None) is None:             # not from the saved graphics: say what it is and why
        why = ctx._why.get(e)
        src = {'param': 'parametric rebuild from stored parameters', 'bbox': 'box at the stored bounding box', 'line': 'curve', 'approx': 'approximate rebuild'}.get(res[1], res[1])
        try: res[0].info = {'source': src, 'flags': [], 'reason': why or ('no saved-graphics path for class ' + r['class'] if res[1] in ('bbox', 'approx') else None)}
        except Exception: pass
    return res

def _element_mesh(ctx, e, r):
    if r['class'] in CONTAINER_CLASSES: return None
    if (r['class'] not in ANALYTIC_CLASSES or r['class'] in MESH_FIRST) and (ctx.bbox(e) is not None or e not in ctx.eh or r['class'] in MESH_FIRST):
        rm = reader_mesh(ctx, e)
        if rm and r['class'] in MESH_FIRST and ctx.bbox(e) is None:          # no stored box to validate against: check the saved graphics against the parametric rebuild instead
            try:
                pm = BUILDERS[r['class']](ctx, e, r)
                if pm and pm[0] and box_iou(rm[0].v.min(0), rm[0].v.max(0), pm[0].v.min(0), pm[0].v.max(0)) < 0.5: rm = None
            except Exception: pass
        if rm: return rm
    if ctx.catname(e) in ('Planting', 'Entourage') and ctx.bbox(e) is not None and r['class'] == 'FamilyInstance': return geom.ellipsoid(*ctx.bbox(e)), 'bbox'
    if r['class'] == 'FamilyInstance':
        vg = void_geometry(ctx, e, r)
        if vg: return vg
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
            if res and res[0] and res[1] == 'bbox' and _no_3d(ctx, e, r) and getattr(res[0], 'kind', 'tri') == 'tri':
                return feature_edges(res[0]), 'void'                 # oriented placeholder of a symbol without 3D graphics: outline only
            if res and res[0]:
                if r['class'] in ('Floor', 'Ceiling', 'RoofSoffit', 'BuildingPad', 'ProfileRoof', 'FootPrintRoof') and not isinstance(res[0], geom.Multi):
                    col = dominant_rgb(type_layers(ctx, type_of(ctx, e, r)))
                    if col: return geom.Multi([(res[0], col)]), res[1]
                return res
        except Exception as ex:
            if os.environ.get('RVT_DEBUG'): print('builder', r['class'], e, repr(ex))
    if part: return part[0], 'approx'
    if ctx.catname(e) in ('Planting', 'Entourage') and ctx.bbox(e) is not None: return geom.ellipsoid(*ctx.bbox(e)), 'bbox'          # some faces of the decoded body are of an unsupported surface type
    bb = ctx.bbox(e)
    if bb is not None and float(np.min(bb[1] - bb[0])) < 1e-4:          # flat placeholder (a zero-thickness box is a filled plane): the stored curves as lines instead
        try:
            polys = record_curves(r['fields'])
            if polys: return SegSet(polys), 'line'
        except Exception: pass
    if bb is not None and _no_3d(ctx, e, r):      # the family symbol stores no 3D graphics (void-only openings, reference families): an outline, not a solid that would plug the hole it cuts
        return box_edges(*bb), 'void'
    if bb is not None: return geom.box(*bb), 'bbox'
    return None

def feature_edges(m):
    """edges of a triangle mesh where the two adjacent faces are not coplanar (a box -> its 12 edges) as a SegSet"""
    V = np.asarray(m.v, float); F = np.asarray(m.f).reshape(-1, 3)
    N = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    key = lambda p: tuple(np.round(p, 5)); adj = {}
    for t, f in enumerate(F):
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            k = tuple(sorted((key(V[a]), key(V[b])))); adj.setdefault(k, []).append(t)
    segs = [[np.array(k[0]), np.array(k[1])] for k, ts in adj.items() if len(ts) != 2 or abs(float(N[ts[0]] @ N[ts[1]])) < 0.999]
    return SegSet(segs)

def _no_3d(ctx, e, r):
    """family instance whose symbol (and itself) stores no 3D graphics: Revit has no solid for it either (Volume 0, no geometry in its export; reader WHY-BOXY 2026-10-13)"""
    w = str(ctx._why.get(e) or '')
    return 'symbol_no_graphics' in w or (r['class'] == 'FamilyInstance' and 'no_saved_graphics' in w)

def box_edges(lo, hi):
    c = [np.array([(hi if i & 1 else lo)[0], (hi if i & 2 else lo)[1], (hi if i & 4 else lo)[2]]) for i in range(8)]
    return SegSet([[c[a], c[b]] for a, b in ((0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7))])

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
            if abs(float(np.asarray(x)[2])) > abs(float(np.asarray(y)[2])): x, y, u0, u1, v0 = y, x, v0, v1, u0          # axes stored the other way round (x up, y along the line: 2024 Snowdon grids 1-8)
            pts = np.array([o + x * u0 + y * v0, o + x * u1 + y * v0])
        if pts is None: continue
        out.append({'id': e, 'name': r['fields'].get('m_text', ''), 'pts': [[round(float(a) * 0.3048, 4) for a in p] for p in pts]})
    return out

# ---------------------------------------------------------------- main

def write_quick_preview(outdir, q, path):
    """first picture within ~1-2 s of opening: the Rust element table (class, category, bounding box) -> levels, grids and one box per element; meta.json phase 'preview' with quick=True"""
    names = reader.category_names(); els = []; res = []
    for eid, v in q['elements'].items():
        bb = v.get('bbox')
        if not bb or v.get('category') in (None, -1) or str(v['class']).endswith('Symbol') or v['class'] in CONTAINER_CLASSES: continue
        lo, hi = np.array(bb[0], float), np.array(bb[1], float)
        if np.any(hi < lo): continue
        i = len(els); els.append({'id': int(eid), 'cls': v['class'], 'cat': names.get(str(v['category'])) or 'Category %s' % v['category'], 'name': '', 'type': '', 'level': None, 'fid': 'none', 'isType': False, 'family': '', 'phase': -1, 'bb': [lo, hi], 'i': i})
        b = geom.box(lo, hi); res.append((i, 'bbox', 'tri', [(b.v, b.f, None)]))
    pb, pm, pcovg, _, _ = pack_batches(els, res)
    glb.write_glb(os.path.join(outdir, 'preview.glb.tmp'), pb)
    levels = sorted([{'id': l['id'], 'name': l['name'], 'elev': l['elevation_ft'] * 0.3048} for l in q.get('levels') or [] if l.get('elevation_ft') is not None], key=lambda l: l['elev'])
    meta = {'file': os.path.basename(path), 'levels': levels, 'grids': [], 'rooms': [], 'views': [], 'sheets': [], 'fidLabels': FID_LABEL, 'phases': [], 'defaultHidden': sorted({e['cat'] for e in els if default_hidden(e['cat'])}),
            'stamps': {'reader': reader.reader_stamp(), 'viewer': reader.viewer_stamp()}, 'phase': 'preview', 'quick': True, 'batches': pm, 'bbox': model_bbox(els), 'coverage': {k: dict(v) for k, v in pcovg.items()}, 'coverageByClass': {}, 'bboxAgreement': {},
            'elements': [[e['id'], e['cls'], e['cat'], e['name'], e['type'], e['level'], e['fid'], e['isType'], e['family'], e['phase']] for e in els], 'built': time.time(), 'buildSecs': 0}
    json.dump(meta, open(os.path.join(outdir, 'meta.json.tmp'), 'w'), separators=(',', ':'))
    os.replace(os.path.join(outdir, 'preview.glb.tmp'), os.path.join(outdir, 'preview.glb')); os.replace(os.path.join(outdir, 'meta.json.tmp'), os.path.join(outdir, 'meta.json'))
    return len(els)

STAGES = ['reading', 'tables', 'preview', 'geometry', 'packing', 'done']

def _rss_note():
    """' (rss X.X GB, peak Y.Y GB)' of this process when RVT_LOG_RSS is set"""
    if not os.environ.get('RVT_LOG_RSS'): return ''
    try:
        st = dict(l.split(':', 1) for l in open('/proc/self/status') if l.startswith(('VmRSS', 'VmHWM')))
        return ' (rss %.2f GB, peak %.2f GB)' % (int(st['VmRSS'].split()[0]) / 2 ** 20, int(st['VmHWM'].split()[0]) / 2 ** 20)
    except Exception: return ''

class Progress:
    """writes outdir/progress.json (stage, pct, message, counters, ETA, per-stage seconds) atomically; the server exposes it so the UI can show a progress bar.
    While the reader decodes (no counters of its own yet) a heartbeat thread keeps elapsed time and the reader's own progress file (~/.cache/rvt-progress/*.json, when present) fresh."""
    def __init__(self, outdir, log, size_mb=None, src=None):
        self.dir = outdir; self.log = log; self.t0 = time.time(); self.times = {}; self.ts = time.time(); self.stage = None; self.size_mb = size_mb; self.src = src
        self.extra = {}; self.last = ('', 0.0, ''); self._hb = None
    def eta_total(self):
        """rough total seconds from earlier conversions (seconds per MB, ~/.cache/rvt-viewer/timing.json)"""
        try: rate = json.load(open(os.path.join(reader.CACHE_DIR, 'timing.json'))).get('s_per_mb')
        except Exception: rate = None
        return round(self.size_mb * rate) if (rate and self.size_mb) else None
    def set(self, stage, pct=0.0, msg='', **extra):
        now = time.time()
        if self.stage and stage != self.stage: self.times[self.stage] = round(now - self.ts, 2); self.ts = now; self.extra = {}
        self.stage = stage; self.extra.update(extra); self.last = (stage, pct, msg)
        el = now - self.ts; eta = (el * (1 - pct) / pct) if (pct and 0.03 < pct < 1) else None
        d = {'stage': stage, 'stages': STAGES, 'pct': round(pct, 3), 'msg': msg, 'elapsed': round(now - self.t0, 1), 'started': self.t0, 'stage_elapsed': round(el, 1), 'eta_stage': None if eta is None else round(eta, 1),
             'eta_total': self.eta_total(), 'times': self.times, 'size_mb': self.size_mb, 'reader': reader.reader_stamp(), 'updated': now, **self.extra}
        rp = self.reader_progress()
        if rp: d['reader_progress'] = rp
        try:
            fn = os.path.join(self.dir, 'progress.json'); open(fn + '.tmp', 'w').write(json.dumps(d)); os.replace(fn + '.tmp', fn)
        except OSError: pass
        if msg: self.log('[%s] %s%s' % (stage, msg, _rss_note()))
    def reader_progress(self):
        """the Rust/Python reader's own progress file for this input, if it writes one: ~/.cache/rvt-progress/<hash>.json with the input path inside"""
        if not self.src: return None
        try:
            import glob
            try:                                       # only this input's progress file (rvt_fast.file_key), not a glob of the whole directory every second
                RF = _rf(); k = RF.file_key(self.src) if RF is not None and hasattr(RF, 'file_key') else None
                f = os.path.expanduser('~/.cache/rvt-progress/%s.json' % k) if k else None
                if f and os.path.exists(f) and time.time() - os.path.getmtime(f) <= 600:
                    d = json.load(open(f))
                    if os.path.abspath(str(d.get('file') or d.get('path') or d.get('input') or '')) == os.path.abspath(self.src): return d
                if f: return None
            except Exception: pass
            for f in glob.glob(os.path.expanduser('~/.cache/rvt-progress/*.json')):
                if time.time() - os.path.getmtime(f) > 600: continue
                d = json.load(open(f))
                if os.path.abspath(str(d.get('file') or d.get('path') or d.get('input') or '')) == os.path.abspath(self.src): return d
        except Exception: pass
        return None
    def start_heartbeat(self):
        import threading
        stop = threading.Event()
        def beat():
            while not stop.wait(1.0):
                st, pct, msg = self.last
                if st == 'reading': self.set(st, pct, '', **self.extra)
        self._hb = stop; threading.Thread(target=beat, daemon=True).start()
    def stop_heartbeat(self):
        if self._hb: self._hb.set()

_G = {}      # fork-shared state for the geometry workers

def _geo_chunk(rng):
    ctx, els = _G['ctx'], _G['els']; out = []
    for i in range(*rng):
        el = els[i]
        if not el['cat'] or el['isType']: continue
        try: res = element_mesh(ctx, el['id'], ctx.recs[el['id']])
        except Exception: res = None
        if res is None: continue
        mesh, fid = res
        parts = [(pm.v, pm.f, rgb, getattr(pm, 'mat', None)) for pm, rgb in (mesh.parts if isinstance(mesh, geom.Multi) else [(mesh, None)])]
        out.append((i, fid, getattr(mesh, 'kind', 'tri'), parts, getattr(mesh, 'info', None)))
    return out

def geometry_cache_key():
    import hashlib as _h
    d = os.path.dirname(os.path.abspath(__file__)); h = _h.md5(reader.reader_stamp().encode())
    src = open(os.path.join(d, 'build.py')).read(); a = src.index('# ---------------------------------------------------------------- geometry builders'); b = src.index('# ---------------------------------------------------------------- datum / spatial')
    h.update(src[a:b].encode()); h.update(repr(sorted(CLASS_CAT.items())).encode())          # which classes get geometry at all depends on CLASS_CAT
    for f in ('geom.py', 'occ.py', 'brep.py', 'build_util.py', 'materials.py'): h.update(open(os.path.join(d, f), 'rb').read())
    return h.hexdigest()[:12]

def run_geometry(ctx, els, prog, workers=None, on_partial=None):
    """per-element geometry, cached on disk by (reader stamp + geometry source) and computed in parallel worker processes (fork: the decoded model is shared copy-on-write)"""
    import pickle, multiprocessing as mp
    key = geometry_cache_key(); fn = os.path.join(reader.CACHE_DIR, 'geom-%s-%s.pkl' % (hashlib.md5(ctx.raw_key.encode()).hexdigest()[:10], key))
    if os.path.exists(fn) and not os.environ.get('RVT_NO_GEOM_CACHE'):
        t = time.time(); res = pickle.load(open(fn, 'rb')); prog.set('geometry', 1.0, 'geometry cache hit (%.1fs)' % (time.time() - t), done=len(els), total=len(els), cache_hit=True); return res
    ensure_roofs(ctx); prefetch_reader_meshes(ctx, els, prog, on_partial)
    _G['ctx'] = ctx; _G['els'] = els
    n = len(els); step = 150; chunks = [(a, min(a + step, n)) for a in range(0, n, step)]
    nw = workers or _mesh_workers(); res = []                  # bounded by the memory cap (forked workers dirty copy-on-write pages of the parent)
    if nw == 1 or n < 400:
        for k, c in enumerate(chunks): res += _geo_chunk(c); prog.set('geometry', (k + 1) / len(chunks), '', done=min(n, (k + 1) * step), total=n)
    else:
        last_partial = time.time(); done_el = 0
        with mp.get_context('fork').Pool(nw) as pool:
            for k, r in enumerate(pool.imap_unordered(_geo_chunk, chunks)):
                res += r; done_el = min(n, (k + 1) * step)
                prog.set('geometry', 0.4 + 0.6 * (k + 1) / len(chunks), 'geometry %d/%d chunks (%d workers)' % (k + 1, len(chunks), nw) if k % 10 == 0 else '', done=done_el, total=n, sub='Building meshes (%d workers)' % nw)
                if on_partial and k + 1 < len(chunks) and time.time() - last_partial > float(os.environ.get('RVT_PARTIAL_SECS', '12')): on_partial(res, done_el, n); last_partial = time.time()
    res.sort(key=lambda t: t[0])
    try: pickle.dump(res, open(fn + '.tmp', 'wb'), protocol=5); os.replace(fn + '.tmp', fn)
    except Exception: pass
    return res

SMOOTH = os.environ.get('RVT_SMOOTH', '1') != '0'
SMOOTH_COS = np.cos(np.radians(35.0))
def smooth_part(pv, pf):
    """vertex normals for a triangle part: weld coincident vertices, area-weighted average of the incident (signed) face normals; a corner takes the vertex normal when it is within 35 deg
    of its own face, else it gets its own vertex carrying the flat face normal (hard edges stay crisp, curved surfaces shade smooth). The sign of a normal is irrelevant: the viewer flips it
    toward the flat screen-space normal per fragment (reader winding is not consistent). -> (positions, faces, normals)"""
    pv = np.asarray(pv, np.float64); pf = np.asarray(pf, np.int64).reshape(-1, 3)
    if len(pf) == 0: return pv, pf, np.zeros_like(pv)
    if not os.environ.get('RVT_NO_RUST_SMOOTH'):          # Rust drop-in, bit-identical (c3-rust 2026-10-17, tests/diff_smooth.py)
        try:
            RF = _rf(); r = RF.smooth_part(pv, pf, SMOOTH_COS) if RF is not None and hasattr(RF, 'smooth_part') else None
            if r is not None: return r
        except Exception: pass
    q = np.round(pv * 2e4).astype(np.int64)                                   # 0.05 mm (feet)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True); inv = inv.reshape(-1)
    W = pv[first]; wf = inv[pf]
    fn = np.cross(pv[pf[:, 1]] - pv[pf[:, 0]], pv[pf[:, 2]] - pv[pf[:, 0]])
    ln = np.linalg.norm(fn, axis=1); ok = ln > 1e-12; fu = np.zeros_like(fn); fu[ok] = fn[ok] / ln[ok, None]
    N = np.zeros_like(W)
    for k in range(3): np.add.at(N, wf[:, k], fn)
    nl = np.linalg.norm(N, axis=1); N = np.divide(N, nl[:, None], out=np.zeros_like(N), where=nl[:, None] > 1e-12)
    sm = np.einsum('ij,ikj->ik', fu, N[wf]) > SMOOTH_COS                      # (faces, 3) corner uses the shared vertex normal
    flat = ~sm & ok[:, None]; nf = int(flat.sum())
    pos = np.vstack([W, pv[pf][flat]]); nrm = np.vstack([N, np.repeat(fu[:, None, :], 3, 1)[flat]])
    idx = wf.copy(); idx[flat] = len(W) + np.arange(nf)
    return pos, idx, nrm

def pack_batches(els, res, previews=False, mats=None):
    """merge per-element parts into one indexed mesh per (category, kind, translucency, colour); parts may carry a material (position in `mats`): its colour / transparency are used and the
    per-vertex _MAT attribute lets the viewer draw procedural textures and 'colour by material'"""
    acc = {}; covg = collections.defaultdict(collections.Counter); covc = collections.defaultdict(collections.Counter); ious = {}
    got = {t[0]: t for t in res}; ML = (mats or {}).get('list') or []
    for i, el in enumerate(els):
        t = got.get(i)
        if t is None: covg[el['cat'] or '(none)']['none'] += 1; el['fid'] = 'none'; continue
        fid, kind, parts = t[1], t[2], t[3]; el['ginfo'] = t[4] if len(t) > 4 else None
        if fid in ('param', 'solid') and el['bb'] is not None:
            allv = np.vstack([p[0] for p in parts]); el['iou'] = round(box_iou(allv.min(0), allv.max(0), *el['bb']), 3); ious.setdefault(el['cat'], []).append(el['iou'])
            if fid == 'param' and (el['iou'] >= 0.97 or contained_match(allv.min(0), allv.max(0), *el['bb'])): fid = 'matched'
        el['fid'] = fid; covg[el['cat']][fid] += 1; covc[el['cls']][fid] += 1
        transl = (fid == 'bbox' and el['cat'] in TRANSLUCENT_CATS) or fid == 'pending' or 'void' in ((el['ginfo'] or {}).get('flags') or [])
        used = set()
        for part in parts:
            pv, pf, rgb = part[0], part[1], part[2]; mi = part[3] if len(part) > 3 else None
            tr = transl; mrec = ML[mi] if (mi is not None and mi < len(ML) and fid not in ('bbox', 'pending')) else None
            if mrec is not None:
                used.add(mi)
                if rgb is None: rgb = tuple(mrec['rgb'])
                if mrec['alpha'] < 0.97 and not transl: tr = round(max(0.08, mrec['alpha']) * 20) / 20          # glass etc.: its own translucent batch
            hexc = None if rgb is None else '%02x%02x%02x' % tuple(int(x * 255) for x in rgb)
            a = acc.setdefault((el['cat'], kind, tr, hexc), {'pos': [], 'idx': [], 'eidx': [], 'mat': [], 'ranges': [], 'nv': 0, 'nt': 0})
            pn = None
            if kind == 'tri' and len(pf) and SMOOTH: pv, pf, pn = smooth_part(pv, pf)
            a.setdefault('nrm', []).append(pn if pn is not None else np.zeros((len(pv), 3)))
            a['pos'].append(pv); a['idx'].append(pf.reshape(-1) + a['nv']); a['eidx'].append(np.full(len(pv), i, np.float32)); a['mat'].append(np.full(len(pv), -1 if mrec is None else mi, np.float32))
            a['ranges'] += [i, a['nt'], len(pf)]; a['nv'] += len(pv); a['nt'] += len(pf)
        el['mats'] = sorted(used)
    batches = []; bmeta = []
    for (cat, kind, tr, hexc), a in acc.items():
        nrm = np.vstack(a['nrm']) if kind == 'tri' and SMOOTH else None; nrm = None if nrm is None else np.stack([nrm[:, 0], nrm[:, 2], -nrm[:, 1]], 1).astype(np.float32)
        pos = glb.to_yup_m(np.vstack(a['pos'])); idx = np.concatenate(a['idx']).astype(np.uint32)
        c = (0.1, 0.1, 0.12) if kind == 'line' else (tuple(int(hexc[k:k + 2], 16) / 255 for k in (0, 2, 4)) if hexc else cat_color(cat))
        if isinstance(tr, float) and not isinstance(tr, bool): alpha = tr
        else: alpha = 0.45 if (cat in ('Windows', 'Curtain Panels') and not hexc) else ((0.08 if cat in ('Planting', 'Entourage') else 0.14) if tr else 1.0)      # a known material decides (glass carries its own transparency)
        matv = np.concatenate(a['mat']) if ML and kind == 'tri' else None
        batches.append({'name': cat + ('' if kind == 'tri' else ' (lines)'), 'color': (*c, alpha), 'pos': pos, 'eidx': np.concatenate(a['eidx']), 'idx': idx, 'mode': 1 if kind == 'line' else 4, 'mat': matv, 'nrm': nrm})
        bmeta.append({'cat': cat, 'kind': kind, 'color': '#%02x%02x%02x' % tuple(int(x * 255) for x in c), 'alpha': alpha, 'ranges': a['ranges'], 'tris': a['nt']})
    return batches, bmeta, covg, covc, ious

def model_bbox(els):
    allb = [el['bb'] for el in els if el['bb'] is not None and el['fid'] != 'none' and not default_hidden(el['cat'] or '') and el['cat'] not in ('Mass',)]
    if not allb: allb = [el['bb'] for el in els if el['bb'] is not None and el['fid'] != 'none']
    if not allb: return [[0, 0, 0], [0, 0, 0]]
    lo = np.percentile([b[0] for b in allb], 0.5, axis=0) * 0.3048; hi = np.percentile([b[1] for b in allb], 99.5, axis=0) * 0.3048
    if len(allb) < 50: lo = np.minimum(lo, np.min([b[0] for b in allb], 0) * 0.3048); hi = np.maximum(hi, np.max([b[1] for b in allb], 0) * 0.3048)
    return [lo.tolist(), hi.tolist()]

def write_summary(outdir, meta, src=None):
    tot = {}; hid = set(meta.get('defaultHidden') or [])
    for c, v in meta['coverage'].items():
        if c in hid: continue                                    # analytical / reference / annotation-like categories are not building geometry
        for k, n in v.items(): tot[k] = tot.get(k, 0) + n
    tr, mt, ap, bx = tot.get('solid', 0) + tot.get('mesh', 0), tot.get('matched', 0), tot.get('param', 0) + tot.get('approx', 0), tot.get('bbox', 0); ex = tr + mt; n = max(ex + ap + bx, 1)
    sm = {'file': meta['file'], 'src': src and os.path.abspath(src), 'size': os.path.getsize(src) if src and os.path.exists(src) else None, 'mtime': os.path.getmtime(src) if src and os.path.exists(src) else None, 'built': meta.get('built'), 'elements': len(meta['elements']),
          'tris': sum(b['tris'] for b in meta['batches']), 'exact': ex / n, 'true': tr / n, 'matched': mt / n, 'approx': ap / n, 'box': bx / n, 'stamps': meta.get('stamps'), 'secs': meta.get('buildSecs')}
    json.dump(sm, open(os.path.join(outdir, 'summary.json'), 'w'))

def convert(path, outdir, log=print, workers=None):
    """rvt -> outdir. Stages (progress.json): reading (reader), tables (+sqlite), preview (boxes only: meta.json phase=preview + preview.glb, usable at once), geometry (parallel,
    cached), packing (model.glb, final meta.json phase=done)."""
    import pickle
    os.makedirs(outdir, exist_ok=True); prog = Progress(outdir, log, size_mb=os.path.getsize(path) / 1e6, src=path); T = {}; cold = [True]
    def rlog(m):
        log(m)
        if 'raw cache hit' in m: cold[0] = False; prog.extra['raw_cache_hit'] = True
    prog.set('reading', 0.0, 'decoding %s with the reader' % os.path.basename(path)); prog.start_heartbeat()
    def _preimport():                                   # heavy first-time imports (OpenCascade ~2 s, scipy, matplotlib) overlap the Rust reader (c2-rust NEEDS 19); joined before any fork
        for mod in ('rvtviewer.occ', 'scipy.spatial', 'scipy.optimize', 'matplotlib.path'):
            try: __import__(mod)
            except Exception: pass
    import threading; pre = threading.Thread(target=_preimport, daemon=True)          # started after the quick preview: the first picture must not wait for the GIL
    VF = fast_module(); fm = None; t = time.time()
    if VF is not None:
        try:
            fm = VF.open(path); q = fm.quick(); nq = write_quick_preview(outdir, q, path); T['quick'] = round(time.time() - t, 2)
            prog.extra['quick_boxes'] = nq; prog.extra['fast_path'] = True; prog.set('reading', 0.0, 'element table in %.1fs: %d boxes, %d levels (full decode continues)' % (T['quick'], nq, len(q.get('levels') or [])), quick_rev=1)
            pre.start(); raw = VF.load(path, rlog, model=fm)
        except (KeyboardInterrupt, SystemExit): raise
        except BaseException as ex:                                    # incl. Rust panics
            log('Rust fast path failed (%r): using the Python reader' % ex); fm = None; pre.is_alive() and pre.join(); raw = reader.cached_load(path, rlog)
    else: raw = reader.cached_load(path, rlog)
    T['reader'] = round(time.time() - t, 2); ctx = Ctx(raw); ctx.fm = fm; prog.stop_heartbeat()
    if cold[0]:                                                          # remember the cold decode speed for ETAs
        try:
            tf = os.path.join(reader.CACHE_DIR, 'timing.json'); old = json.load(open(tf)) if os.path.exists(tf) else {}
            old['s_per_mb'] = round(T['reader'] / max(os.path.getsize(path) / 1e6, 0.5), 3); json.dump(old, open(tf, 'w'))
        except Exception: pass
    ctx.src = path
    from . import materials as MT
    ctx.mats = MT.load(path, log)
    try:
        reader._import(); import rvt_geometry as GG; GG.file_geometry_index(path)        # load the reader's geometry context before the worker processes fork
        if fm is not None: GG._docs[path] = fm.doc()                                       # element_brep / body_materials use the Rust-backed document
    except Exception: pass
    ctx.raw_key = '%s|%s|%s|%s' % (os.path.abspath(path), os.path.getmtime(path), os.path.getsize(path), reader.reader_stamp())
    from . import datums
    prog.set('tables', 0.0, 'building element tables')
    t = time.time(); els = build_table(ctx)
    levels = build_levels(ctx); lvl_by_id = {e: n for e, (n, z) in ctx.levels.items()}
    for i, el in enumerate(els):
        el['i'] = i; r = ctx.recs[el['id']]; p = ctx.par.get(el['id'], {}).get('params', {}); lv = None
        for k in ('m_assocLevelId', 'm_levelId', 'm_scheduleOnlyLevelId'):
            v = ctx.eid_int(r['fields'].get(k)) if k in r['fields'] else None
            if v in lvl_by_id: lv = v; break
        if lv is None:
            for k in ('Level', 'Base Constraint', 'Schedule Level', 'Base Level', 'Reference Level'):
                v = ctx.eid_int(p.get(k)) if isinstance(p.get(k), int) else None
                if v in lvl_by_id: lv = v; break
        el['level'] = lvl_by_id.get(lv)
    views, sheets = datums.views_sheets(ctx); rooms = datums.rooms(ctx, lvl_by_id); grids = build_grids(ctx)
    try:      # per-view display options (visual style, background sky/ground colours, silhouettes), reader rvt_viewdisp: the viewer opens a stored view in its own style
        if os.environ.get('RVT_VIEWDISP_IN_CONVERT'):      # off by default: the reader pass costs a second extraction on cold files; rvtviewer/viewdisp.py fills it in after the model is usable
            import rvt_viewdisp
            vd = rvt_viewdisp.view_display(path); VS = {1: 'wireframe', 2: 'hiddenline', 7: 'consistent', 3: 'shaded', 4: 'shaded', 5: 'shaded', 6: 'shaded'}
            for v_ in views:
                d_ = vd.get(v_.get('id'))
                if d_ and d_.get('surfaces') is not None:
                    v_['display'] = {'surfaces': d_['surfaces'], 'vstyle': VS.get(d_['surfaces']), 'silhouettes': d_.get('silhouettes'), 'bg': d_.get('background_type'), 'sky': d_.get('sky_color'), 'ground': d_.get('ground_color'),
                                     'shadows': d_.get('cast_shadows'), 'hidden_lines': d_.get('hidden_lines')}
    except Exception as ex: log('view display options skipped: %r' % (ex,))
    ph_names, ph_ids = datums.phases(ctx)
    for el in els:
        v = ctx.par.get(el['id'], {}).get('params', {}).get('Phase Created'); el['phase'] = ph_ids.get(ctx.eid_int(v), -1) if isinstance(v, int) else -1
    idx_of = {el['id']: el['i'] for el in els}
    for r_ in rooms: r_['i'] = idx_of.get(r_['id'])
    # sqlite first (inspector / search work from the preview on); fidelity + iou are updated at the end
    dbp = os.path.join(outdir, 'model.sqlite')
    if os.path.exists(dbp): os.remove(dbp)
    db = sqlite3.connect(dbp)
    db.executescript('create table el(i integer primary key, id integer, cls text, cat text, name text, type text, family text, level text, uid text, ifc text, fid text, bb text, iou real, type_i integer);'
                     'create table prm(i integer, k text, v text); create table ginfo(i integer primary key, info text);')
    db.executemany('insert into el values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', [(el['i'], el['id'], el['cls'], el['cat'], el['name'], el['type'], el['family'], el.get('level'), el['uid'], el['ifc'], 'none',
                    '[[%r,%r,%r],[%r,%r,%r]]' % (*el['bb'][0].tolist(), *el['bb'][1].tolist()) if el['bb'] else None, None, idx_of.get(el['typeId'])) for el in els])
    rows = []; sg = 1 << (8 * ctx.W - 1)
    for el in els:
        for k, v in ctx.par.get(el['id'], {}).get('params', {}).items():
            if isinstance(v, str): rows.append((el['i'], k, v))
            elif isinstance(v, int) and not isinstance(v, bool): rows.append((el['i'], k, str(ctx.sc(v) if v >= sg else int(v))))
            else: rows.append((el['i'], k, json.dumps(v)))
    db.executemany('insert into prm values(?,?,?)', rows); db.execute('create index prm_i on prm(i)'); db.commit()
    T['tables'] = round(time.time() - t, 2)
    base_meta = {'file': os.path.basename(path), 'levels': levels, 'grids': grids, 'rooms': rooms, 'views': views, 'sheets': sheets, 'fidLabels': FID_LABEL,
                 'phases': ph_names, 'defaultHidden': sorted({el['cat'] for el in els if el['cat'] and default_hidden(el['cat'])}), 'stamps': {'reader': reader.reader_stamp(), 'viewer': reader.viewer_stamp()},
                 'elements': None}
    # preview: every element that has a stored bounding box as a plain box (vectorised, ~1 s), written before the expensive geometry
    prog.set('preview', 0.0, 'writing box preview')
    t = time.time(); pres = []
    for i, el in enumerate(els):
        if el['cat'] and not el['isType'] and el['bb'] is not None and el.get('cls') not in CONTAINER_CLASSES: pres.append((i, 'bbox', 'tri', [(geom.box(*el['bb']).v, geom.box(*el['bb']).f, None)]))
    pels = [dict(e) for e in els]
    pb, pm, pcovg, _, _ = pack_batches(pels, pres, mats=ctx.mats)
    glb.write_glb(os.path.join(outdir, 'preview.glb'), pb)
    meta = dict(base_meta); meta.update({'phase': 'preview', 'batches': pm, 'bbox': model_bbox(pels), 'coverage': {k: dict(v) for k, v in pcovg.items()}, 'coverageByClass': {}, 'bboxAgreement': {},
                                         'elements': [[el['id'], el['cls'], el['cat'], el['name'], el['type'], el['level'], el['fid'], el['isType'], el['family'], el['phase']] for el in pels], 'built': time.time(), 'buildSecs': 0})
    json.dump(meta, open(os.path.join(outdir, 'meta.json'), 'w'), separators=(',', ':'))
    T['preview'] = round(time.time() - t, 2)
    prev_by_i = {t_[0]: t_ for t_ in pres}; rev = [1]
    prog.set('geometry', 0.0, 'building geometry', done=0, total=len(els), partial_rev=1)       # rev 1: the full preview (names, levels, grids, rooms) replaces the quick one
    def on_partial(res_, done_el, n_):
        """progressive display: finished elements as real meshes, the rest as translucent ghost boxes; replaces preview.glb + meta.json (phase stays 'preview') so the open page can refresh itself"""
        got = {t_[0] for t_ in res_}; allr = list(res_) + [(i, 'pending', 'tri', prev_by_i[i][3], None) for i in prev_by_i if i not in got]
        pe = [dict(e) for e in els]; b_, m_, cg_, _, _ = pack_batches(pe, allr, mats=ctx.mats)
        glb.write_glb(os.path.join(outdir, 'preview.glb.tmp'), b_)
        mt = dict(base_meta); mt.update({'phase': 'preview', 'batches': m_, 'bbox': model_bbox(pe), 'coverage': {k: dict(v) for k, v in cg_.items()}, 'coverageByClass': {}, 'bboxAgreement': {}, 'pending': sum(1 for i in prev_by_i if i not in got),
                                         'elements': [[e['id'], e['cls'], e['cat'], e['name'], e['type'], e['level'], e['fid'], e['isType'], e['family'], e['phase']] for e in pe], 'built': time.time(), 'buildSecs': 0})
        json.dump(mt, open(os.path.join(outdir, 'meta.json.tmp'), 'w'), separators=(',', ':'))
        os.replace(os.path.join(outdir, 'preview.glb.tmp'), os.path.join(outdir, 'preview.glb')); os.replace(os.path.join(outdir, 'meta.json.tmp'), os.path.join(outdir, 'meta.json'))
        rev[0] += 1; prog.set('geometry', prog.last[1], prog.last[2], partial_rev=rev[0], pending=mt['pending'])
    pre.is_alive() and pre.join()                       # no import may be in flight when the geometry stage forks its workers
    t = time.time(); res = run_geometry(ctx, els, prog, workers, on_partial); T['geometry'] = round(time.time() - t, 2)
    prog.set('packing', 0.0, 'packing glTF (meshes, materials)', done=len(els), total=len(els))
    t = time.time(); batches, bmeta, covg, covc, ious = pack_batches(els, res, mats=ctx.mats)
    glb.write_glb(os.path.join(outdir, 'model.glb'), batches)
    db.executemany('insert into ginfo values(?,?)', [(el['i'], json.dumps(el['ginfo'])) for el in els if el.get('ginfo')])
    db.execute('create table if not exists elmat(i integer, m integer)'); db.executemany('insert into elmat values(?,?)', [(el['i'], m_) for el in els for m_ in (el.get('mats') or [])]); db.execute('create index if not exists elmat_m on elmat(m)')
    use = collections.Counter(m_ for el in els for m_ in (el.get('mats') or []))
    MT.write_images(outdir, ctx.mats, log)
    json.dump({'materials': [{**m_, 'elements': use.get(k, 0)} for k, m_ in enumerate(ctx.mats['list'])], 'textureClasses': MT.TEX_CLASSES}, open(os.path.join(outdir, 'materials.json'), 'w'), separators=(',', ':'))
    db.executemany('update el set fid=?, iou=? where i=?', [(el['fid'], el.get('iou'), el['i']) for el in els if el['fid'] != 'none']); db.commit(); db.close()
    meta = dict(base_meta); meta.update({'phase': 'done', 'batches': bmeta, 'bbox': model_bbox(els), 'coverage': {k: dict(v) for k, v in covg.items()}, 'coverageByClass': {k: dict(v) for k, v in covc.items()},
                                         'bboxAgreement': {k: [round(float(np.mean(v)), 3), len(v)] for k, v in ious.items()}, 'built': time.time(),
                                         'elements': [[el['id'], el['cls'], el['cat'], el['name'], el['type'], el['level'], el['fid'], el['isType'], el['family'], el['phase']] for el in els],
                                         'openBodies': [i for i, el in enumerate(els) if any(b_.get('closed') == 'open' for b_ in ((el.get('ginfo') or {}).get('body_list') or []))]})     # not closed solids: no section cap
    T['packing'] = round(time.time() - t, 2); T['total'] = round(time.time() - prog.t0, 2); meta['buildSecs'] = T['total']; meta['timings'] = T
    json.dump(meta, open(os.path.join(outdir, 'meta.json'), 'w'), separators=(',', ':'))
    write_summary(outdir, meta, path)
    prog.set('done', 1.0, 'wrote %s in %.1fs: %d batches, %d tris  %s' % (outdir, T['total'], len(batches), sum(b['tris'] for b in bmeta), json.dumps(T)))
    return meta
