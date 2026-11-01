"""Synthetic: member_status flags a flipped deflate byte as bad, leaves clean members ok, treats ISIZE!=length as unverifiable (as in undamaged real files)."""
import os, sys, zlib, struct, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from rvtwrite2_gzcheck import member_status
GZH = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0b'
def member(raw, isz=None):
    co = zlib.compressobj(6, zlib.DEFLATED, -15); z = co.compress(raw) + co.flush()
    return GZH + z + struct.pack('<II', zlib.crc32(raw) & 0xffffffff, len(raw) if isz is None else isz)
def build(ms): return b'\0' * 44 + (b'\0' * 32).join(ms)
R = random.Random(1)
RAW = [bytes(R.randrange(0, 40) for _ in range(5000)) for _ in range(4)]
def test_clean():
    assert member_status(build([member(r) for r in RAW])) == ['ok'] * 4
def test_unverifiable():
    ms = [member(RAW[0]), member(RAW[1], isz=len(RAW[1]) - 100), member(RAW[2])]
    assert member_status(build(ms)) == ['ok', 'unv', 'ok']
def test_flip_detected():
    ms = [member(r) for r in RAW]; base = member_status(build(ms)); n = 0
    for i in range(40):
        m = bytearray(ms[1]); off = R.randrange(12, len(m) - 8); m[off] ^= 1 << R.randrange(8)
        st = member_status(build([ms[0], bytes(m), ms[2], ms[3]]))
        if st != base: n += 1
    assert n >= 35, n
