"""unit tests: packing, loop nesting, matching metric, B-rep closedness, cache versioning (run: .venv/bin/python -m pytest tests  or  python tests/test_pipeline.py)"""
import os, sys, tempfile, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtviewer import build, geom, glb, reader, brep

def _els(n):
    return [{'id': 100 + i, 'cls': 'FamilyInstance', 'cat': 'Doors', 'name': 'x', 'type': 't', 'family': 'f', 'level': None, 'isType': False, 'uid': None, 'ifc': None, 'fid': 'none', 'bb': (np.zeros(3), np.ones(3)), 'i': i, 'phase': -1} for i in range(n)]

def test_pack_batches_ranges_and_ids():
    els = _els(3); b0 = geom.box((0, 0, 0), (1, 1, 1)); b1 = geom.box((2, 0, 0), (3, 1, 1))
    res = [(0, 'bbox', 'tri', [(b0.v, b0.f, None)]), (2, 'param', 'tri', [(b1.v, b1.f, (0.5, 0.5, 0.5))])]
    batches, bmeta, covg, covc, ious = build.pack_batches(els, res)
    assert len(batches) == 2                                              # one per (category, colour)
    allr = [m['ranges'] for m in bmeta]; got = sorted(r[k] for r in allr for k in range(0, len(r), 3))
    assert got == [0, 2]                                                  # element indices survive packing
    for b in batches:                                                     # per-vertex element index matches the ranges
        assert set(np.unique(b['eidx']).astype(int)) <= {0, 2}
    assert covg['Doors']['none'] == 1 and els[1]['fid'] == 'none'

def test_glb_has_eidx_and_indices_in_range():
    b = geom.box((0, 0, 0), (1, 1, 1)); p = os.path.join(tempfile.mkdtemp(), 'a.glb')
    glb.write_glb(p, [{'name': 'a', 'color': (1, 1, 1, 1), 'pos': glb.to_yup_m(b.v), 'eidx': np.full(len(b.v), 7.0), 'idx': b.f.reshape(-1)}])
    data = open(p, 'rb').read(); n = int.from_bytes(data[12:16], 'little'); js = json.loads(data[20:20 + n])
    assert js['accessors'][0]['count'] == 8 and js['accessors'][2]['count'] == 36

def test_group_loops_nesting():
    sq = lambda x, y, s: np.array([[x, y], [x + s, y], [x + s, y + s], [x, y + s]], float)
    groups = build.group_loops([sq(0, 0, 10), sq(2, 2, 2), sq(20, 0, 5), sq(3, 3, 0.5)])     # outer + hole (holding an island) + a separate outer
    outers = sorted(len(h) for o, h in groups); assert len(groups) == 3 and outers == [0, 0, 1]

def test_contained_match():
    lo, hi = np.zeros(3), np.array([10, 0.5, 4.0])
    assert build.contained_match(lo, hi, lo - 0.05, hi + np.array([0, 1.5, 0]))          # wall inside a box that also holds attachments
    assert not build.contained_match(lo, hi, lo, np.array([10, 0.5, 8.0]))              # covers only half of the height
    assert not build.contained_match(lo - 1, hi, lo, hi)                                # sticks out of the stored box

def test_brep_open_edge_detection():
    closed = {'m_pEdges': [{'obj': {'m_pFace': [{'ref': 1}, {'ref': 2}]}}]}; opened = {'m_pEdges': [{'obj': {'m_pFace': [{'ref': 1}, None]}}]}
    assert brep.open_edge_count(closed) == 0 and brep.open_edge_count(opened) == 1

def test_prism_volume_with_island_free_hole():
    outer = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float); hole = np.array([[4, 4], [6, 4], [6, 6], [4, 6]], float)
    m = geom.prism([outer, hole], 0, 1); v = m.v; f = m.f
    assert abs(abs(np.einsum('ij,ij->i', v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6) - 96) < 1e-6

def test_reader_stamp_changes_when_reader_files_change():
    d = tempfile.mkdtemp(); open(os.path.join(d, 'rvt_x.py'), 'w').write('a = 1\n'); old = reader.READER_DIR; reader.READER_DIR = d
    try:
        s1 = reader.reader_stamp(); time.sleep(1.1); open(os.path.join(d, 'rvt_x.py'), 'w').write('a = 22\n'); s2 = reader.reader_stamp()
        open(os.path.join(d, 'GEOMETRY_API.md'), 'w').write('api'); s3 = reader.reader_stamp()
        assert s1 != s2 and s2 != s3                                   # reader edit and GEOMETRY_API.md both invalidate converted models
    finally: reader.READER_DIR = old

def test_model_dir_key_depends_on_stamps():
    from rvtviewer import cli
    f = os.path.join(tempfile.mkdtemp(), 'm.rvt'); open(f, 'wb').write(b'x'); a = cli.model_dir(f)
    old = reader.reader_stamp; reader.reader_stamp = lambda: 'zzzz'
    try: b = cli.model_dir(f)
    finally: reader.reader_stamp = old
    assert a != b

def test_viewer_stamp_is_stable_and_nonempty():
    assert reader.viewer_stamp() == reader.viewer_stamp() and len(reader.viewer_stamp()) == 8

if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'): v(); print('ok', k)
