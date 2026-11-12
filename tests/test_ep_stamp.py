import os, pickle, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
PK = os.path.expanduser('~/c3x-tmp-c4x/ddmin/ent.pkl')      # first 700 B of base/ours/Revit-after partitions (local Autodesk sample, c4xaw26)
pytestmark = pytest.mark.skipif(not os.path.exists(PK), reason='local Revit-made pair cache absent')
def test_stamp_entries_reproduces_revit_headers():
    import rvt_ep_stamp as S
    P = pickle.load(open(PK, 'rb'))
    out, n = S.stamp_entries(P['ours'], 0x426, 0x427)
    assert n == 12
    for k in range(1, 13):
        o = 14 + 22 * k
        assert out[o:o + 22] == P['revit'][o:o + 22]
def test_fix_chunk_flag_and_adler():
    """flag byte sits at s+18 INSIDE the adler-covered body (body starts s+16), so the flag must change before the adler is recomputed."""
    import zlib, struct, rvt_ep_stamp as S
    body = bytearray(bytes(range(200)) * 3); body[2] = 0x1f
    s = 48
    part = bytearray(s + 8) + bytearray(4) + bytearray(struct.pack('<I', len(body))) + body
    out = S.fix_chunk(bytes(part), s)
    assert out[s + 18] == 0x1e
    assert struct.unpack_from('<I', out, s + 8)[0] == zlib.adler32(out[s + 16:s + 16 + len(body)])
def test_find_chunks_self_validating():
    import zlib, struct, rvt_ep_stamp as S
    body = bytearray(b'\x9e\x08\x1f' + bytes(range(150)))
    good = bytes(40) + struct.pack('<II', zlib.adler32(bytes(body)), len(body)) + bytes(body)       # s = 40-8 ... header (8B) before adler? see below
    # layout: s+8 adler, s+12 len, s+16 body -> pad 8 bytes of junk before the adler
    s = 32
    part = bytes(s + 8) + struct.pack('<II', zlib.adler32(bytes(body)), len(body)) + bytes(body) + bytes(20)
    assert S.find_chunks(part) == [s]
    bad = bytearray(part); bad[s + 8] ^= 1          # wrong adler: not reported
    assert S.find_chunks(bytes(bad)) == []
