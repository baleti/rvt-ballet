"""Planar B-rep faces from decoded `Geometry` objects (Face + EdgeLoop + Edge with per-side UV end points).
Only plane surfaces are tessellated here; other surface types are reported as skipped so coverage can be shown honestly."""
import numpy as np
from .build_util import g
from . import geom
from .geom import Mesh

def _unwrap(o):
    return o['obj'] if isinstance(o, dict) and 'obj' in o else o

def face_polygons(geo):
    """-> (list of (plane(o,x,y), [loop uv arrays...])), n_skipped"""
    geo = _unwrap(geo)
    faces = geo.get('m_pFaces') or []; edges = geo.get('m_pEdges') or []
    emap = {}
    for e in edges:
        if isinstance(e, dict) and e.get('handle') is not None and e.get('obj'): emap[e['handle']] = e['obj']
    out = []; skipped = 0
    for fs in faces:
        fo = _unwrap(fs); fh = fs.get('handle')
        surf = _unwrap(fo.get('m_pSurf')) if fo.get('m_pSurf') else None
        if surf and surf.get('type') in ('cone', 'sphere', 'torus', 'revolution', 'bspline', 'ruled', 'cylinder', 'plane') and 'type' in surf:
            pl = ('occ', surf)                      # reader-provided surface schema (NEEDS-FROM-READER.md section 1): tessellated through OpenCascade (occsurf)
        elif surf and 'm_radius' in surf and 'm_zVec' in surf and 'm_center' in surf and 'm_xVec' in surf:
            pl = ('cyl', np.array(surf['m_center'], float), np.array(surf['m_xVec'], float), np.array(surf['m_yVec'], float), np.array(surf['m_zVec'], float), float(surf['m_radius']))
        elif not surf or 'm_xVec' not in surf or 'm_origin' not in surf or 'm_yVec' not in surf: skipped += 1; continue
        else: pl = (np.array(surf['m_origin'], float), np.array(surf['m_xVec'], float), np.array(surf['m_yVec'], float))
        loops = []; loop_s = fo.get('m_pFirstLoop'); guard = 0
        while loop_s and guard < 64:
            guard += 1
            lo = _unwrap(loop_s); lh = loop_s.get('handle') if isinstance(loop_s, dict) else None
            first = (lo.get('m_next') or {}).get('ref')
            pts = trace_loop(emap, fh, lh, first)
            if pts is not None and len(pts) >= 3: loops.append(pts)
            nl = lo.get('m_nextLoop')
            loop_s = nl if isinstance(nl, dict) and nl.get('obj') else None
        if loops: out.append((pl, loops))
        else: skipped += 1
    return out, skipped

def trace_loop(emap, fh, lh, first):
    pts = []; cur = first; seen = set(); prev_end = None
    while cur is not None and cur != lh and cur not in seen:
        e = emap.get(cur)
        if e is None: return None
        seen.add(cur)
        faces = e.get('m_pFace') or []
        s = next((k for k, f in enumerate(faces) if isinstance(f, dict) and f.get('ref') == fh), None)
        if s is None: return None
        fl = e.get('m_firstAndLastEdgePnts') or []
        if len(fl) < 2: return None
        a = np.array(fl[0]['uv'][s], float); b = np.array(fl[1]['uv'][s], float)
        inter = [np.array(p['uv'][s], float) if isinstance(p, dict) and 'uv' in p else np.array(p, float) for p in (e.get('m_interiorEdgePnts') or [])]
        seq = [a] + inter + [b]
        if prev_end is not None and np.linalg.norm(seq[0] - prev_end) > np.linalg.norm(seq[-1] - prev_end): seq = seq[::-1]
        elif prev_end is None:
            nx = (e.get('m_next') or [None, None])[s]
            n2 = emap.get(nx['ref']) if isinstance(nx, dict) and 'ref' in nx else None
            if n2 is not None:
                s2 = next((k for k, f in enumerate(n2.get('m_pFace') or []) if isinstance(f, dict) and f.get('ref') == fh), None)
                if s2 is not None:
                    q = [np.array(p['uv'][s2], float) for p in (n2.get('m_firstAndLastEdgePnts') or [])[:2]]
                    if len(q) == 2 and min(np.linalg.norm(seq[0] - q[0]), np.linalg.norm(seq[0] - q[1])) < min(np.linalg.norm(seq[-1] - q[0]), np.linalg.norm(seq[-1] - q[1])): seq = seq[::-1]
        pts.extend(seq[:-1]); prev_end = seq[-1]
        nx = (e.get('m_next') or [None, None])[s]
        cur = nx.get('ref') if isinstance(nx, dict) else None
    return np.array(pts) if pts else None

def open_edge_count(geo):
    """edges bounding only one face: a closed solid has none (some stored bodies are open shells, e.g. a top surface without bottom)"""
    n = 0
    for e in _unwrap(geo).get('m_pEdges') or []:
        eo = _unwrap(e)
        if not isinstance(eo, dict): continue
        fs = eo.get('m_pFace') or []
        if len([f for f in fs if f]) < 2: n += 1
    return n

def geometry_mesh(geo):
    """Mesh (feet) from all planar/cylindrical faces; returns (mesh, n_planar, n_skipped); open shells count their open edges as skipped"""
    polys, skipped = face_polygons(geo)
    skipped += 1 if open_edge_count(geo) else 0
    m = Mesh(); n = 0
    for pl, loops in polys:
        loops = [l for l in loops if len(l) >= 3]
        if not loops: continue
        areas = [abs(0.5 * np.sum(l[:, 0] * np.roll(l[:, 1], -1) - np.roll(l[:, 0], -1) * l[:, 1])) for l in loops]
        order = np.argsort(areas)[::-1]; ls = [loops[i] for i in order]
        try: pts, idx = geom.polygon_tris(ls)
        except Exception: skipped += 1; continue
        if isinstance(pl[0], str) and pl[0] == 'occ':
            from . import occsurf
            try: m.add(occsurf.tessellate_face(pl[1], ls)); n += 1
            except Exception: skipped += 1
            continue
        if isinstance(pl[0], str):
            _, c, x, y, z, R = pl; u = pts[:, :1]; w = pts[:, 1:2]
            v = c + R * (np.cos(u) * x + np.sin(u) * y) + w * z
        else:
            o, x, y = pl; v = o + pts[:, :1] * x + pts[:, 1:2] * y
        m.add(Mesh(v, idx)); n += 1
    return m, n, skipped

_SKIP = frozenset(('m_pParamValueSetDouble', 'm_pParamValueSetInt', 'm_pParamValueSetAString', 'm_pParamValueSetElementId', 'm_cellList', 'm_docAccess', 'm_faceHistTable', 'm_edgeHistTable',
                  'm_curveHistTableSet', 'm_edgeHistTableReverse', 'm_pGeomTable', 'm_pInstParams', 'm_pParams', 'm_oUserData', 'm_pCurveDriver', 'm_pCrv', 'm_exposedFaceMap', 'm_affectedEdgesTags', 'm_pRefFaces'))

def find_geometries(o, key_ok=lambda k: True, out=None, depth=0):
    """all `Geometry` objects (dicts with m_pFaces + m_pEdges) inside a record"""
    if out is None: out = []
    if isinstance(o, dict):
        if 'm_pFaces' in o and 'm_pEdges' in o and o.get('m_pFaces'): out.append(o); return out
        for k, v in o.items():
            if k in _SKIP or not key_ok(k): continue
            if isinstance(v, (dict, list)): find_geometries(v, key_ok, out, depth + 1)
    elif isinstance(o, list):
        for v in o: find_geometries(v, key_ok, out, depth + 1)
    return out


def reader_components(geo):
    """shells of a Geometry body from the reader's rvt_mesh.components (None if the reader module is not available); thin adapter, falls back to this module's own tessellation"""
    try:
        from . import reader; reader._import()
        import rvt_mesh
        return rvt_mesh.components(_unwrap(geo))
    except Exception:
        return None
