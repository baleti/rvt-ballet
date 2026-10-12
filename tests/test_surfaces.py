"""one test per OpenCascade surface type: tessellated area against closed-form values (run: .venv/bin/python tests/test_surfaces.py)"""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtviewer import occsurf

X, Y = [1, 0, 0], [0, 1, 0]


def area(m): return float(np.linalg.norm(np.cross(m.v[m.f[:, 1]] - m.v[m.f[:, 0]], m.v[m.f[:, 2]] - m.v[m.f[:, 0]]), axis=1).sum() / 2)
def rect(u0, u1, v0, v1): return [[(u0, v0), (u1, v0), (u1, v1), (u0, v1)]]


def test_plane():
    assert abs(area(occsurf.tessellate_face({'type': 'plane', 'origin': [0, 0, 0], 'xdir': X, 'ydir': Y}, rect(0, 3, 0, 2))) - 6) < 1e-6


def test_cylinder():
    m = occsurf.tessellate_face({'type': 'cylinder', 'origin': [0, 0, 0], 'xdir': X, 'ydir': Y, 'radius': 2}, rect(0, math.pi, 0, 5))
    assert abs(area(m) - math.pi * 2 * 5) / (math.pi * 10) < 0.01


def test_cone():
    a = math.radians(30); L = 4.0; r0 = 1.0; r1 = r0 + L * math.sin(a); exact = math.pi * (r0 + r1) * L     # frustum lateral area
    m = occsurf.tessellate_face({'type': 'cone', 'origin': [0, 0, 0], 'xdir': X, 'ydir': Y, 'ref_radius': r0, 'semi_angle': a}, rect(0, 2 * math.pi, 0, L))
    assert abs(area(m) - exact) / exact < 0.01


def test_sphere():
    m = occsurf.tessellate_face({'type': 'sphere', 'origin': [0, 0, 0], 'xdir': X, 'ydir': Y, 'radius': 1.5}, rect(0, 2 * math.pi, -math.pi / 2 + 0.01, math.pi / 2 - 0.01))
    assert abs(area(m) - 4 * math.pi * 1.5 ** 2) / (4 * math.pi * 2.25) < 0.02


def test_torus():
    R, r = 3.0, 0.5; exact = 4 * math.pi ** 2 * R * r
    m = occsurf.tessellate_face({'type': 'torus', 'origin': [0, 0, 0], 'xdir': X, 'ydir': Y, 'major_radius': R, 'minor_radius': r}, rect(0, 2 * math.pi, 0, 2 * math.pi))
    assert abs(area(m) - exact) / exact < 0.02


def test_revolution():
    prof = {'type': 'line', 'p0': [1, 0, 0], 'p1': [2, 0, 3]}; exact = math.pi * 3 * math.sqrt(10)          # a revolved line is a cone frustum
    m = occsurf.tessellate_face({'type': 'revolution', 'profile': prof, 'axis_origin': [0, 0, 0], 'axis_dir': [0, 0, 1]})
    assert abs(area(m) - exact) / exact < 0.01


def test_bspline_flat_patch():
    P = [[[0, 0, 0], [0, 3, 0]], [[4, 0, 0], [4, 3, 0]]]                                                       # bilinear patch 4 x 3
    s = {'type': 'bspline', 'poles': P, 'uknots': [0, 1], 'vknots': [0, 1], 'umults': [2, 2], 'vmults': [2, 2], 'udegree': 1, 'vdegree': 1}
    assert abs(area(occsurf.tessellate_face(s)) - 12) < 1e-6


def test_nurbs_quarter_cylinder():
    w = math.sqrt(2) / 2; ring = [(1, 0), (1, 1), (0, 1)]; ws = [1, w, 1]                                       # rational quadratic quarter circle swept 2 along z: area = pi/2 * 2
    P = [[[x, y, z] for z in (0, 2)] for (x, y) in ring]; W = [[ws[i], ws[i]] for i in range(3)]
    s = {'type': 'bspline', 'poles': P, 'weights': W, 'uknots': [0, 1], 'vknots': [0, 1], 'umults': [3, 3], 'vmults': [2, 2], 'udegree': 2, 'vdegree': 1}
    assert abs(area(occsurf.tessellate_face(s)) - math.pi) / math.pi < 0.01


def test_ruled():
    s = {'type': 'ruled', 'curve1': {'type': 'line', 'p0': [0, 0, 0], 'p1': [5, 0, 0]}, 'curve2': {'type': 'line', 'p0': [0, 2, 1], 'p1': [5, 2, 1]}}
    assert abs(area(occsurf.tessellate_face(s)) - 5 * math.sqrt(5)) < 1e-4


def test_ruled_full_knot_vector():
    c1 = {'type': 'bspline', 'degree': 1, 'poles': [[0, 0, 0], [5, 0, 0]], 'knots': [0, 0, 1, 1]}
    c2 = {'type': 'bspline', 'degree': 1, 'poles': [[0, 2, 1], [5, 2, 1]], 'knots': [0, 0, 1, 1]}
    assert abs(area(occsurf.tessellate_face({'type': 'ruled', 'curve1': c1, 'curve2': c2})) - 5 * math.sqrt(5)) < 1e-4


def test_hermite_flat_patch():
    nodes = [{'p': [x, y, 0.0], 'tu': [1, 0, 0], 'tv': [0, 1, 0], 'twist': [0, 0, 0]} for y in (0, 3) for x in (0, 4)]       # bilinear Hermite patch 4 x 3 with unit tangents
    s = {'type': 'hermite', 'uparams': [0, 4], 'vparams': [0, 3], 'nodes': nodes}
    assert abs(area(occsurf.tessellate_face(s)) - 12) < 1e-6


def test_trimmed_with_hole():
    s = {'type': 'plane', 'origin': [0, 0, 0], 'xdir': X, 'ydir': Y}
    loops = [[(0, 0), (10, 0), (10, 10), (0, 10)], [(4, 4), (6, 4), (6, 6), (4, 6)]]
    assert abs(area(occsurf.tessellate_face(s, loops)) - 96) < 0.5


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'): v(); print('ok', k)
