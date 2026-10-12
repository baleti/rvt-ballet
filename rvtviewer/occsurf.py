"""Tessellation of any analytic surface type through OpenCascade Geom surfaces, from a plain-dict surface schema (see NEEDS-FROM-READER.md section 1).
A face = surface definition + trim loops in the surface's (u, v) parameter space. Triangulation: Delaunay over the densified uv loops plus a refinement grid (cells outside the loops dropped),
then every vertex is evaluated on the OCC surface (Geom_*Surface.Value), so cones, tori, surfaces of revolution, B-spline/NURBS and ruled surfaces all use the same code path.
Units: whatever the caller uses (feet in the viewer), angles in radians."""
import math
import numpy as np
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax3, gp_Ax1
from OCP.Geom import (Geom_Plane, Geom_CylindricalSurface, Geom_ConicalSurface, Geom_SphericalSurface, Geom_ToroidalSurface, Geom_SurfaceOfRevolution,
                      Geom_BSplineSurface, Geom_BSplineCurve)
from OCP.OCP.collections import Array1_gp_Pnt as TColgp_Array1OfPnt, Array2_gp_Pnt as TColgp_Array2OfPnt, Array1_double as TColStd_Array1OfReal, Array1_int as TColStd_Array1OfInteger, Array2_double as TColStd_Array2OfReal
from OCP.GeomFill import GeomFill
from OCP.GC import GC_MakeSegment, GC_MakeArcOfCircle
from .geom import Mesh


def _ax3(s):
    z = s.get('axis') or np.cross(s['xdir'], s['ydir'])
    return gp_Ax3(gp_Pnt(*[float(v) for v in s['origin']]), gp_Dir(*[float(v) for v in z]), gp_Dir(*[float(v) for v in s['xdir']]))


def _curve(c):
    """rail / profile curve dict -> Geom_Curve.  {'type':'line','p0','p1'} | {'type':'arc','p0','mid','p1'} | {'type':'bspline','poles','degree','knots','mults'[,'weights']}"""
    t = c['type']
    if t == 'line': return GC_MakeSegment(gp_Pnt(*c['p0']), gp_Pnt(*c['p1'])).Value()
    if t == 'arc': return GC_MakeArcOfCircle(gp_Pnt(*c['p0']), gp_Pnt(*c['mid']), gp_Pnt(*c['p1'])).Value()
    if t == 'bspline':
        P = c['poles']; poles = TColgp_Array1OfPnt(1, len(P))
        for i, p in enumerate(P): poles.SetValue(i + 1, gp_Pnt(*[float(v) for v in p]))
        knots, mults = list(c['knots']), c.get('mults')
        if mults is None:                                                           # the reader may give the full (repeated) knot vector instead of distinct knots + multiplicities
            dk = []; mults = []
            for k in knots:
                if dk and abs(k - dk[-1]) < 1e-12: mults[-1] += 1
                else: dk.append(k); mults.append(1)
            knots = dk
        kn = TColStd_Array1OfReal(1, len(knots)); mu = TColStd_Array1OfInteger(1, len(mults))
        for i, k in enumerate(knots): kn.SetValue(i + 1, float(k))
        for i, m in enumerate(mults): mu.SetValue(i + 1, int(m))
        if c.get('weights'):
            w = TColStd_Array1OfReal(1, len(P))
            for i, v in enumerate(c['weights']): w.SetValue(i + 1, float(v))
            return Geom_BSplineCurve(poles, w, kn, mu, int(c['degree']))
        return Geom_BSplineCurve(poles, kn, mu, int(c['degree']))
    raise ValueError('curve type ' + t)


class _P:
    __slots__ = ('x', 'y', 'z')
    def __init__(s_, v): s_.x, s_.y, s_.z = float(v[0]), float(v[1]), float(v[2])
    def X(s_): return s_.x
    def Y(s_): return s_.y
    def Z(s_): return s_.z


class HermiteSurface:
    """bicubic Hermite patch grid: nodes u-fastest, each {'p','tu','tv','twist'}; uparams / vparams = node parameters. Value(u, v) -> point (OCC-like accessor)"""
    def __init__(self, s):
        self.up = np.asarray(s['uparams'], float); self.vp = np.asarray(s['vparams'], float); nu = len(self.up)
        N = s['nodes']; self.P = np.array([[N[j * nu + i]['p'] for i in range(nu)] for j in range(len(self.vp))], float)
        self.TU = np.array([[N[j * nu + i]['tu'] for i in range(nu)] for j in range(len(self.vp))], float)
        self.TV = np.array([[N[j * nu + i]['tv'] for i in range(nu)] for j in range(len(self.vp))], float)
        self.TW = np.array([[N[j * nu + i].get('twist', [0, 0, 0]) for i in range(nu)] for j in range(len(self.vp))], float)
    @staticmethod
    def _h(t):
        return np.array([2 * t ** 3 - 3 * t ** 2 + 1, -2 * t ** 3 + 3 * t ** 2, t ** 3 - 2 * t ** 2 + t, t ** 3 - t ** 2])
    def Value(self, u, v):
        i = int(np.clip(np.searchsorted(self.up, u) - 1, 0, len(self.up) - 2)); j = int(np.clip(np.searchsorted(self.vp, v) - 1, 0, len(self.vp) - 2))
        du = self.up[i + 1] - self.up[i]; dv = self.vp[j + 1] - self.vp[j]; hu = self._h((u - self.up[i]) / du); hv = self._h((v - self.vp[j]) / dv)
        out = np.zeros(3)
        for a, (ii, ub) in enumerate(((i, 0), (i + 1, 1))):
            for b, (jj, vb) in enumerate(((j, 0), (j + 1, 1))):
                out += self.P[jj, ii] * hu[a] * hv[b] + self.TU[jj, ii] * du * hu[2 + a] * hv[b] + self.TV[jj, ii] * dv * hu[a] * hv[2 + b] + self.TW[jj, ii] * du * dv * hu[2 + a] * hv[2 + b]
        return _P(out)
    def Bounds(self): return (self.up[0], self.up[-1], self.vp[0], self.vp[-1])


def make_surface(s):
    """surface dict -> (Geom_Surface, default (u0,u1,v0,v1), kind)
    plane      {'type':'plane','origin','xdir','ydir'}                          u,v = distances along xdir, ydir
    cylinder   {'type':'cylinder','origin','xdir','ydir','radius'}               u angle, v height along axis = xdir x ydir
    cone       {'type':'cone','origin','xdir','ydir','ref_radius','semi_angle'}  u angle, v distance along the generatrix from the reference circle
    sphere     {'type':'sphere','origin','xdir','ydir','radius'}                 u longitude, v latitude
    torus      {'type':'torus','origin','xdir','ydir','major_radius','minor_radius'}
    revolution {'type':'revolution','profile':<curve dict>,'axis_origin','axis_dir'}   u angle about the axis, v = profile curve parameter
    bspline    {'type':'bspline','poles': [[[x,y,z] per v] per u], 'weights': same shape (optional), 'uknots','vknots','umults','vmults','udegree','vdegree'}
    ruled      {'type':'ruled','curve1':<curve dict>,'curve2':<curve dict>}      u along the curves, v 0..1 between them"""
    t = s['type']
    if t == 'plane': return Geom_Plane(_ax3(s)), (-1e3, 1e3, -1e3, 1e3), t
    if t == 'cylinder': return Geom_CylindricalSurface(_ax3(s), float(s['radius'])), (0, 2 * math.pi, -1e3, 1e3), t
    if t == 'cone': return Geom_ConicalSurface(_ax3(s), float(s['semi_angle']), float(s['ref_radius'])), (0, 2 * math.pi, -1e3, 1e3), t
    if t == 'sphere': return Geom_SphericalSurface(_ax3(s), float(s['radius'])), (0, 2 * math.pi, -math.pi / 2, math.pi / 2), t
    if t == 'torus': return Geom_ToroidalSurface(_ax3(s), float(s['major_radius']), float(s['minor_radius'])), (0, 2 * math.pi, 0, 2 * math.pi), t
    if t == 'revolution':
        ax = gp_Ax1(gp_Pnt(*[float(v) for v in s['axis_origin']]), gp_Dir(*[float(v) for v in s['axis_dir']]))
        c = _curve(s['profile']); return Geom_SurfaceOfRevolution(c, ax), (0, 2 * math.pi, c.FirstParameter(), c.LastParameter()), t
    if t == 'bspline':
        P = s['poles']; nu, nv = len(P), len(P[0]); poles = TColgp_Array2OfPnt(1, nu, 1, nv)
        for i in range(nu):
            for j in range(nv): poles.SetValue(i + 1, j + 1, gp_Pnt(*[float(v) for v in P[i][j]]))
        uk = TColStd_Array1OfReal(1, len(s['uknots'])); vk = TColStd_Array1OfReal(1, len(s['vknots']))
        um = TColStd_Array1OfInteger(1, len(s['umults'])); vm = TColStd_Array1OfInteger(1, len(s['vmults']))
        for i, k in enumerate(s['uknots']): uk.SetValue(i + 1, float(k))
        for i, k in enumerate(s['vknots']): vk.SetValue(i + 1, float(k))
        for i, k in enumerate(s['umults']): um.SetValue(i + 1, int(k))
        for i, k in enumerate(s['vmults']): vm.SetValue(i + 1, int(k))
        if s.get('weights'):
            w = TColStd_Array2OfReal(1, nu, 1, nv)
            for i in range(nu):
                for j in range(nv): w.SetValue(i + 1, j + 1, float(s['weights'][i][j]))
            surf = Geom_BSplineSurface(poles, w, uk, vk, um, vm, int(s['udegree']), int(s['vdegree']))
        else: surf = Geom_BSplineSurface(poles, uk, vk, um, vm, int(s['udegree']), int(s['vdegree']))
        b = surf.Bounds(); return surf, tuple(b), t
    if t == 'ruled':
        surf = GeomFill.Surface_s(_curve(s['curve1']), _curve(s['curve2'])); b = surf.Bounds(); return surf, tuple(b), t
    if t == 'hermite':
        h = HermiteSurface(s); return h, tuple(h.Bounds()), t
    raise ValueError('surface type ' + t)


def _densify(loop, step):
    out = []; L = np.asarray(loop, float)
    for a, b in zip(L, np.roll(L, -1, axis=0)):
        n = max(1, int(np.max(np.abs(b - a) / step))); out += [a + (b - a) * k / n for k in range(n)]
    return np.array(out)


def tessellate_face(s, loops_uv=None, angular=math.radians(8)):
    """-> Mesh of the surface restricted to the uv loops (outer first, then holes); loops_uv=None = the whole default parameter rectangle (finite surfaces only).
    Resolution: `angular` radians in periodic directions, 1/24 of the parameter span elsewhere."""
    from matplotlib.path import Path as _P
    from scipy.spatial import Delaunay
    surf, dom, kind = make_surface(s)
    if loops_uv is None: loops_uv = [[(dom[0], dom[2]), (dom[1], dom[2]), (dom[1], dom[3]), (dom[0], dom[3])]]
    L = [np.asarray(l, float) for l in loops_uv if len(l) >= 3]
    allp = np.vstack(L); lo, hi = allp.min(0), allp.max(0)
    span = np.maximum(hi - lo, 1e-9)
    if kind in ('cylinder', 'cone'): su, sv = angular, span[1] / 8
    elif kind == 'sphere': su, sv = angular, math.pi / 12
    elif kind == 'torus': su, sv = angular, angular
    elif kind == 'revolution': su, sv = angular, span[1] / 16
    elif kind == 'hermite': su, sv = span[0] / 16, span[1] / 16
    else: su, sv = span[0] / 24, span[1] / 24
    step = np.array([su, sv])
    ring = [_densify(l, step) for l in L]
    gx, gy = np.meshgrid(np.arange(lo[0] + su / 2, hi[0], su), np.arange(lo[1] + sv / 2, hi[1], sv)); grid = np.c_[gx.ravel(), gy.ravel()]
    outer = _P(ring[0]); inside = outer.contains_points(grid)
    for h in ring[1:]: inside &= ~_P(h).contains_points(grid)
    pts = np.vstack(ring + [grid[inside]])
    tri = Delaunay(pts).simplices; cen = pts[tri].mean(1); keep = outer.contains_points(cen)
    for h in ring[1:]: keep &= ~_P(h).contains_points(cen)
    tri = tri[keep]
    V = np.array([[p.X(), p.Y(), p.Z()] for p in (surf.Value(float(u), float(v)) for u, v in pts)])
    return Mesh(V, tri.astype(np.int32))
