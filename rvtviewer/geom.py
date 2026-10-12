"""Mesh primitives in Revit model space (feet, Z up). A Mesh is (V Nx3 float64, F Mx3 int32); flat normals are computed at export."""
import math
import numpy as np

FT = 0.3048

class Multi:
    """several coloured parts of one element; v/f expose the union (volume / bbox checks use it)"""
    def __init__(self, parts): self.parts = [(m, c) for m, c in parts if m]; 
    @property
    def v(self): return np.vstack([m.v for m, _ in self.parts]) if self.parts else np.zeros((0, 3))
    @property
    def f(self):
        off = 0; out = []
        for m, _ in self.parts: out.append(m.f + off); off += len(m.v)
        return np.vstack(out) if out else np.zeros((0, 3), np.int32)
    def __bool__(self): return bool(self.parts)

class Mesh:
    __slots__ = ('v', 'f', 'info', 'face_types', 'mat')
    def __init__(self, v=None, f=None):
        self.info = None; self.face_types = None; self.mat = None
        self.v = np.zeros((0, 3)) if v is None else np.asarray(v, float).reshape(-1, 3)
        self.f = np.zeros((0, 3), np.int32) if f is None else np.asarray(f, np.int32).reshape(-1, 3)
    def __bool__(self): return len(self.f) > 0
    def add(self, o):
        if not o: return self
        self.f = np.vstack([self.f, o.f + len(self.v)]); self.v = np.vstack([self.v, o.v]); return self
    def transform(self, M):
        """M: 4x4 (or 3x4) matrix, applied to points"""
        M = np.asarray(M, float); self.v = self.v @ M[:3, :3].T + M[:3, 3]; return self
    def bbox(self):
        return (self.v.min(0), self.v.max(0)) if len(self.v) else None

def box(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    c = np.array([[x, y, z] for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])])
    f = [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4), (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]
    return Mesh(c, f)

def obox(origin, ux, uy, uz):
    """parallelepiped spanned by three edge vectors from origin"""
    o = np.asarray(origin, float); ux = np.asarray(ux, float); uy = np.asarray(uy, float); uz = np.asarray(uz, float)
    m = box((0, 0, 0), (1, 1, 1))
    m.v = o + m.v[:, :1] * ux + m.v[:, 1:2] * uy + m.v[:, 2:] * uz
    # keep outward winding if the frame is left-handed
    if np.dot(np.cross(ux, uy), uz) < 0: m.f = m.f[:, ::-1]
    return m

def polygon_tris(loops):
    """triangulate a planar polygon with holes: loops = [outer Nx2, hole Nx2, ...] -> (verts Kx2, faces Mx3)"""
    import mapbox_earcut as ec
    pts = np.vstack(loops).astype(np.float64); ends = np.cumsum([len(l) for l in loops]).astype(np.uint32)
    idx = ec.triangulate_float64(pts, ends).reshape(-1, 3)
    return pts, idx.astype(np.int32)

def prism(loops, z0, z1):
    """vertical prism from 2D loops (outer first, holes after) between z0 and z1"""
    loops = [np.asarray(l, float) for l in loops if len(l) >= 3]
    if not loops: return Mesh()
    pts, idx = polygon_tris(loops)
    n = len(pts)
    zf0 = z0 if callable(z0) else (lambda xy, c=z0: np.full(len(xy), c)); zf1 = z1 if callable(z1) else (lambda xy, c=z1: np.full(len(xy), c))
    top = np.c_[pts, zf1(pts)]; bot = np.c_[pts, zf0(pts)]
    # orient cap triangles: up on top, down on bottom
    a = pts[idx[:, 1]] - pts[idx[:, 0]]; b = pts[idx[:, 2]] - pts[idx[:, 0]]
    sgn = np.sign((a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])); sgn[sgn == 0] = 1
    idx = np.where(sgn[:, None] > 0, idx, idx[:, ::-1])
    v = [top, bot]; f = [idx, (idx + n)[:, ::-1]]
    off = 2 * n
    # side walls: each loop edge a quad; outer ccw-outward, holes cw-outward is automatic when we orient by signed area
    for li, l in enumerate(loops):
        area = 0.5 * np.sum(l[:, 0] * np.roll(l[:, 1], -1) - np.roll(l[:, 0], -1) * l[:, 1])
        ll = l if (area > 0) == (li == 0) else l[::-1]
        m = len(ll); nxt = np.roll(ll, -1, axis=0)
        sv = np.vstack([np.c_[ll, zf0(ll)], np.c_[nxt, zf0(nxt)], np.c_[nxt, zf1(nxt)], np.c_[ll, zf1(ll)]])
        i = np.arange(m)
        sf = np.vstack([np.c_[i, i + m, i + 2 * m], np.c_[i, i + 2 * m, i + 3 * m]]) + off
        v.append(sv); f.append(sf); off += 4 * m
    return Mesh(np.vstack(v), np.vstack(f))

def tube(p0, p1, radius, seg=12, cap=True):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d)
    if L < 1e-9: return Mesh()
    d /= L
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(d, a); u /= np.linalg.norm(u); w = np.cross(d, u)
    t = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    ring = np.cos(t)[:, None] * u + np.sin(t)[:, None] * w
    v = np.vstack([p0 + radius * ring, p1 + radius * ring])
    i = np.arange(seg); j = (i + 1) % seg
    f = np.vstack([np.c_[i, j, i + seg], np.c_[j, j + seg, i + seg]])
    if cap:
        c0 = len(v); v = np.vstack([v, p0, p1])
        f = np.vstack([f, np.c_[j, i, np.full(seg, c0)], np.c_[i + seg, j + seg, np.full(seg, c0 + 1)]])
    return Mesh(v, f)

def rect_tube(p0, p1, width, height, up=(0, 0, 1)):
    """rectangular duct/tray between p0 and p1; width horizontal (perp to axis & up), height along up-ish"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d)
    if L < 1e-9: return Mesh()
    d /= L; up = np.asarray(up, float)
    s = np.cross(d, up)
    if np.linalg.norm(s) < 1e-6: s = np.cross(d, np.array([1.0, 0, 0]))
    s /= np.linalg.norm(s); u = np.cross(s, d)
    return obox(p0 - s * width / 2 - u * height / 2, d * L, s * width, u * height)

def sweep_polyline(pts, radius, seg=10):
    m = Mesh()
    for a, b in zip(pts[:-1], pts[1:]): m.add(tube(a, b, radius, seg))
    return m

def arc_points(center, radius, a0, a1, normal=(0, 0, 1), xaxis=(1, 0, 0), maxdeg=10):
    c = np.asarray(center, float); n = np.asarray(normal, float); n = n / np.linalg.norm(n)
    x = np.asarray(xaxis, float); x = x - n * np.dot(x, n); x /= np.linalg.norm(x); y = np.cross(n, x)
    k = max(2, int(abs(a1 - a0) / math.radians(maxdeg)) + 1)
    t = np.linspace(a0, a1, k + 1)
    return c + radius * (np.cos(t)[:, None] * x + np.sin(t)[:, None] * y)

def chain_loops(segs, tol=1e-3):
    """segs: list of point arrays (each Nx3, a polyline). Join end-to-end into closed loops. -> list of Nx3 arrays (open polylines if not closed)"""
    segs = [np.asarray(s, float) for s in segs if len(s) >= 2]
    used = [False] * len(segs); loops = []
    for i in range(len(segs)):
        if used[i]: continue
        used[i] = True; cur = list(segs[i])
        grew = True
        while grew:
            grew = False
            if np.linalg.norm(cur[0] - cur[-1]) < tol and len(cur) > 2: break
            for j in range(len(segs)):
                if used[j]: continue
                s = segs[j]
                if np.linalg.norm(s[0] - cur[-1]) < tol: cur.extend(s[1:]); used[j] = True; grew = True; break
                if np.linalg.norm(s[-1] - cur[-1]) < tol: cur.extend(s[-2::-1]); used[j] = True; grew = True; break
                if np.linalg.norm(s[-1] - cur[0]) < tol: cur = list(s[:-1]) + cur; used[j] = True; grew = True; break
                if np.linalg.norm(s[0] - cur[0]) < tol: cur = list(s[:0:-1]) + cur; used[j] = True; grew = True; break
        if np.linalg.norm(cur[0] - cur[-1]) < tol: cur = cur[:-1]
        loops.append(np.array(cur))
    return loops


def ellipsoid(lo, hi, nu=16, nv=10):
    """UV ellipsoid inscribed in the box lo..hi (placeholder for tree-like shapes)"""
    lo = np.asarray(lo, float); hi = np.asarray(hi, float); c = (lo + hi) / 2; r = (hi - lo) / 2
    th = np.linspace(0, math.pi, nv + 1); ph = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    v = np.array([[math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t)] for t in th for p in ph]) * r + c
    f = []
    for i in range(nv):
        for j in range(nu):
            a = i * nu + j; b = i * nu + (j + 1) % nu; c2 = (i + 1) * nu + j; d = (i + 1) * nu + (j + 1) % nu
            f += [(a, b, c2), (b, d, c2)]
    return Mesh(v, f)
