"""unit tests for geometry primitives (run: .venv/bin/python -m pytest tests or python tests/test_geom.py)"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtviewer import geom, glb

def vol(m):
    v = m.v; f = m.f
    return abs(np.einsum('ij,ij->i', v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6)

def test_box_volume(): assert abs(vol(geom.box((0, 0, 0), (2, 3, 4))) - 24) < 1e-9
def test_obox_volume(): assert abs(vol(geom.obox((1, 1, 1), (2, 0, 0), (0, 3, 0), (0, 0, 4))) - 24) < 1e-9
def test_prism_with_hole():
    outer = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float); hole = np.array([[4, 4], [6, 4], [6, 6], [4, 6]], float)
    assert abs(vol(geom.prism([outer, hole], 0, 2)) - (100 - 4) * 2) < 1e-6
def test_prism_sloped():
    outer = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float)
    m = geom.prism([outer], lambda xy: np.zeros(len(xy)), lambda xy: 1 + 0.1 * xy[:, 0])   # top plane z = 1 + 0.1 x -> mean height 1.5
    assert abs(vol(m) - 150) < 1e-6
def test_tube_volume():
    m = geom.tube((0, 0, 0), (0, 0, 10), 1.0, seg=360)
    assert abs(vol(m) - np.pi * 10) < 0.01
def test_chain_loops():
    segs = [np.array([[0, 0, 0], [1, 0, 0]]), np.array([[1, 1, 0], [1, 0, 0]]), np.array([[1, 1, 0], [0, 1, 0]]), np.array([[0, 0, 0], [0, 1, 0]])]
    l = geom.chain_loops(segs); assert len(l) == 1 and len(l[0]) == 4
def test_glb_roundtrip(tmp_path=None):
    import tempfile, struct, json
    p = os.path.join(tempfile.mkdtemp(), 'x.glb'); m = geom.box((0, 0, 0), (1, 1, 1))
    glb.write_glb(p, [{'name': 'a', 'color': (1, 0, 0, 1), 'pos': glb.to_yup_m(m.v), 'eidx': np.zeros(len(m.v)), 'idx': m.f.reshape(-1)}])
    b = open(p, 'rb').read(); assert b[:4] == b'glTF'; n = struct.unpack_from('<I', b, 12)[0]; js = json.loads(b[20:20 + n]); assert js['meshes'][0]['primitives'][0]['attributes']['_EIDX'] == 1

def test_hermite_curve_points():
    from rvtviewer import build
    c = {'m_NodeArray': [{'m_iParametr': 0.0, 'm_iPoint': [0, 0, 0], 'm_iTangent': [1, 0, 0]}, {'m_iParametr': 2.0, 'm_iPoint': [2, 0, 0], 'm_iTangent': [1, 0, 0]}]}
    P = build.curve_pts(c); assert P is not None and abs(P[-1][0] - 2) < 1e-9 and np.allclose(P[:, 1:], 0) and np.all(np.diff(P[:, 0]) > 0)
def test_body_summary_closed_box():
    from rvtviewer import build
    m = geom.box((0, 0, 0), (1, 2, 3)); P = m.v[m.f].reshape(-1, 3)
    b = build.body_summary(P, [7] * len(m.f), list(range(len(m.f))))
    assert len(b) == 1 and b[0]['closed'] == 'yes' and abs(b[0]['area'] - 22) < 1e-6

if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'): v(); print('ok', k)
