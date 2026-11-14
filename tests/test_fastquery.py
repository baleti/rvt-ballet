"""fastquery: (1) synthetic primitives (no .rvt bytes): Stream pread over a scattered CFB chain, inflate_run (libdeflate and zlib) == zlib per segment,
ElementHeader candidate ids are a superset of planted header positions; (2) Autodesk samples 2018-2026: fastquery.sheets == fastquery.scan()['sheets'] exactly
(skipped when the corpus is absent). Run: python -m pytest tests/test_fastquery.py"""
import os, sys, io, zlib, struct, json, random, tempfile
import numpy as np
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import fastquery as Q

CORPUS = os.path.expanduser('~/rvt-research/corpus')
SAMPLES = ['2018/09_rac_advanced_sample_project.rvt', '2020/22_rme_basic_sample_project.rvt', '2021/27_Technical_school-current_m.rvt', '2022/32_Arch_Link_Model.rvt',
           '2023/41_rme_advanced_sample_project.rvt', '2024/42_Snowdon_Towers_Sample_HVAC.rvt', '2026/55_Snowdon_Towers_Sample_Structural.rvt']


def segment(payload, footer_tag=0x1234):
    """stored form of one partition segment: [24-byte header][gzip header][deflate][CRC32][ISIZE][8-byte footer]"""
    c = zlib.compressobj(6, zlib.DEFLATED, -15); body = c.compress(payload) + c.flush()
    gz = bytes.fromhex('1f8b080000000000000b') + body + struct.pack('<II', zlib.crc32(payload) & 0xffffffff, len(payload))
    ln = len(gz) + 8
    return struct.pack('<6I', 4, 0, ln, len(payload), 0x65, 0) + gz + struct.pack('<HIH', footer_tag, ln, footer_tag)


class FakeEntry: pass


class FakeOle:
    """olefile stand-in: 512-byte sectors in a scattered FAT chain, the image written to a real file (Stream reads with os.pread)"""
    def __init__(self, stored, order, path):
        self.sectorsize = 512; self.minisectorcutoff = 4096; nsec = -(-len(stored) // 512)
        n = nsec + 3; self.fat = [0xFFFFFFFF] * n; img = bytearray(512 * (n + 1)); pos = {}
        for k, s in enumerate(order(list(range(nsec)))): pos[k] = s; img[(s + 1) * 512:(s + 2) * 512] = stored[k * 512:(k + 1) * 512].ljust(512, b'\0')
        for k in range(nsec): self.fat[pos[k]] = pos[k + 1] if k + 1 < nsec else 0xFFFFFFFE
        e = FakeEntry(); e.size = len(stored); e.isectStart = pos[0]; self.direntries = [e]
        open(path, 'wb').write(bytes(img))
    def _find(self, name): return 0


def paged(data):
    out = bytearray()
    for i in range(0, len(data), Q.PAGE_PAYLOAD):
        pg = data[i:i + Q.PAGE_PAYLOAD]; out += pg
        if len(pg) == Q.PAGE_PAYLOAD: out += b'\xee' * (Q.PAGE_STORED - Q.PAGE_PAYLOAD)
    return bytes(out)


def test_stream_and_inflate():
    rnd = random.Random(5)
    payloads = [bytes(rnd.randrange(256) for _ in range(rnd.randrange(500, 70000))) for _ in range(5)] + [b'abc' * 30000, b'']
    stream = b''.join(segment(p) for p in payloads); segs = []; a = 0
    for p in payloads:
        ln = struct.unpack_from('<I', stream, a + 8)[0]; segs.append((a + 24, ln, len(p))); a += 24 + ln
    stored = paged(stream)
    for order in (lambda r: r, lambda r: r[::-1], lambda r: random.Random(3).sample(r, len(r))):
        with tempfile.TemporaryDirectory() as d:
            fn = os.path.join(d, 'img'); o = FakeOle(stored, order, fn); S = Q.Stream(o, 'x'); fd = os.open(fn, os.O_RDONLY)
            try:
                assert S.payload(fd, 0, len(stream)) == stream
                assert S.payload(fd, 70000, 70100) == stream[70000:70100]           # crosses a page trailer
                buf = S.payload(fd, segs[1][0], segs[-1][0] + segs[-1][1])
                for force_zlib in ('1', ''):
                    os.environ['RVT_Q_ZLIB'] = force_zlib; Q._LD.clear()
                    assert Q.inflate_run(buf, segs[1][0], segs[1:]) == b''.join(payloads[1:])
            finally:
                os.close(fd); os.environ.pop('RVT_Q_ZLIB', None); Q._LD.clear()


def test_inflate_bad_isize_falls_back():
    p = b'xyz' * 1000; s = bytearray(segment(p)); ln = struct.unpack_from('<I', s, 8)[0]
    struct.pack_into('<I', s, 24 + ln - 12, 5)              # wrong ISIZE: libdeflate result is refused, zlib inflates the segment
    assert Q.inflate_run(bytes(s), 0, [(24, ln, len(p))]) == p


def test_eh_candidates_superset():
    W = 8; EH = 0x1a2b; ids = np.array(sorted({5, 77, 1000, 123456, 1 << 40}), np.uint64)
    Q._G.update(W=W, EH=EH, ids=ids)
    buf = bytearray(os.urandom(50000)); planted = []
    for k, (e, back) in enumerate(((77, 8 + W), (1000, 4 + W), (1 << 40, 8 + W))):
        p = 1000 + 9000 * k + k                              # any alignment
        struct.pack_into('<Q', buf, p, e); struct.pack_into('<H', buf, p + back, EH); planted.append(e)
    got = set(Q._eh_candidate_ids(bytes(buf)).tolist())
    assert set(planted) <= got and got <= set(ids.tolist())


def test_subclasses_follow_flagged_parent_tags():
    cls = [{'name': 'Element', 'parent': None}, {'name': 'DBView', 'parent': 12}, {'name': 'TableView', 'parent': 13}, {'name': 'DBViewSchedule', 'parent': 0x8000 | 14},
           {'name': 'AppInfo', 'parent': None}, {'name': 'DBViewInfo', 'parent': 16}]
    assert Q.subclasses(cls, 'DBView') == {'DBView', 'TableView', 'DBViewSchedule'}


def _samples():
    return [os.path.join(CORPUS, s) for s in SAMPLES if os.path.exists(os.path.join(CORPUS, s))]


def test_sheets_equal_scan_on_samples():
    """sheets() (views/viewports/revisions/groups only) == scan()['sheets'] (the summary pass) on every sample year"""
    ss = _samples()
    if not ss:
        import pytest; pytest.skip('Autodesk corpus absent')
    for p in ss:
        a = Q.scan(p, counts=False, workers=4)['sheets']; b = Q.sheets(p, workers=4)
        assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str), p


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_'): f(); print('ok', n)


def test_collect_covers_full_scan_and_names_types():
    """collect('Level'/'Grid'/'View') finds every level, grid and view the full scan lists (it may add group-owned copies the scan skips: at most 2 per sample);
    wall types carry their SymbolInfo names (no-STOP decoder)"""
    import collections
    p = os.path.join(CORPUS, '2019/15_rac_advanced_sample_project.rvt')
    if not os.path.exists(p):
        import pytest; pytest.skip('Autodesk corpus absent')
    a = Q.scan(p, counts=False, workers=4)
    lv = Q.collect(p, 'Level', workers=4); gr = Q.collect(p, 'Grid', workers=4); vw = Q.collect(p, 'View', workers=4)
    A = collections.Counter(l['name'] for l in a['levels']); B = collections.Counter(r['name'] for r in lv)
    assert not (A - B) and sum((B - A).values()) <= 2
    assert not (collections.Counter(a['grids']) - collections.Counter(r['name'] for r in gr))
    Av = collections.Counter((v['name'], v['class']) for v in a['views']) + collections.Counter((s['name'], 'DBViewDrafting') for s in a['sheets'])
    assert not (Av - collections.Counter((r['name'], r['class']) for r in vw))
    wt = Q.collect(p, 'WallType', workers=4)
    assert wt and all(r['name'] for r in wt)
    walls = Q.collect(p, 'Wall', workers=4)
    assert walls and sum(1 for r in walls if r['type_name']) >= 0.95 * len(walls) and all(r['category'] == 'Walls' for r in walls)
    doors = Q.collect(p, category='Doors', workers=4)
    assert doors and all(r['class'] == 'FamilyInstance' and r['category'] == 'Doors' for r in doors)


def test_plain_values():
    class EID(int): pass
    assert Q._plain(EID((1 << 64) - 1)) == -1 and Q._plain([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]
    assert Q._plain({'handle': 1, 'ptr': 2, 'obj': {'m_name': 'T1'}}) == 'T1' and Q._plain({'a': {'b': 1}}) is None


def test_red_rule_and_colours():
    assert Q.is_red((200, 30, 30)) and Q.is_red((0.8, 0.1, 0.15, 1.0)) and not Q.is_red((128, 128, 128)) and not Q.is_red((200, 120, 30))
    assert not Q.is_red((60, 10, 10)) and Q.nearest_name((250, 5, 5)) == 'red'
    assert Q._rgb(6907050) == (170, 100, 105)                    # Revit colour int 0x00BBGGRR (sample brick material)
    tree = {'m_aAProperties': [{'obj': {'m_sName': 'generic_diffuse', 'm_value': [0.9, 0.1, 0.1, 1.0],
                                        'm_aConnected': [{'obj': {'m_aAProperties': [{'obj': {'m_sName': 'tint', 'm_value': [0.2, 0.2, 0.2, 1.0]}}]}}]}},
                               {'obj': {'m_sName': 'other', 'm_value': 3}}]}
    got = Q.asset_colors(tree)
    assert [p for p, _ in got] == ['/generic_diffuse', '/generic_diffuse/tint']


def test_walls_red_material_decodes_everything_on_a_sample():
    p = os.path.join(CORPUS, '2024/46_Snowdon_Towers_Sample_Facades.rvt')
    if not os.path.exists(p):
        import pytest; pytest.skip('Autodesk corpus absent')
    r = Q.walls_red_material(p, workers=4)
    assert r['walls'] and r['walls_with_height'] == r['walls'] and r['walls_with_type'] == r['walls'] and r['materials_with_colour'] == r['materials']
