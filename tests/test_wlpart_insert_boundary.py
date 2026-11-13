"""c5x-rvttype 2026-11-13: insert_at exactly at a member boundary must keep the following original member untouched and give it its OWN frame
(vendor Structural 2024: member 39 is cut mid-record at 131088 bytes, cannot be re-walked; before the fix the insert merged/re-dirtied it and the
output had a member > 131088 or stale X1/X2 frames = Revit CorruptModelException). Synthetic data only."""
import os, sys, struct, zlib, types, pytest
WL = os.path.expanduser('~/rvt-research/write-lab')
if not os.path.isdir(WL): pytest.skip('rvt-research write-lab not present', allow_module_level=True)
sys.path.insert(0, WL)
import wlpart, rvtw

HS = 16

def chain(sizes):
    """record k = [A (not for the first)] filler(HS-8) L body(L); the chain ends with the A of the following record (walk: p += HS + L at p+HS-4)"""
    b = bytearray()
    for k, n in enumerate(sizes): b += (b'\0\0\0\0' if k else b'') + b'\0' * (HS - 8) + struct.pack('<I', n) + b'\1' * n
    return bytes(b) + b'\0\0\0\0'

def gz(raw):
    c = zlib.compressobj(9, zlib.DEFLATED, -15); d = c.compress(raw) + c.flush()
    return rvtw.GZ + b'\0' * 6 + d + struct.pack('<II', zlib.crc32(raw), len(raw))

def partition(raws, x1s):
    P = bytearray(b'\0' * 44)
    for k, raw in enumerate(raws):
        if k:
            P += bytearray(32)
            struct.pack_into('<I', P, len(P) - 32 + 12, x1s[k]); struct.pack_into('<I', P, len(P) - 32 + 20, len(raw) - HS * x1s[k])
        else:
            struct.pack_into('<I', P, 24, x1s[0]); struct.pack_into('<I', P, 32, len(raw) - HS * x1s[0])
        P += gz(raw)
    return bytes(P)

def test_insert_at_boundary_keeps_midrecord_member():
    m0 = chain([30, 40, 50])
    blob = bytes((i * 7 + 3) % 251 for i in range(131088))      # mid-record cut member: not a walkable chain
    m2 = chain([20, 20])
    P = partition([m0, blob, m2], [3, 0, 2])
    p = wlpart.Partition(types.SimpleNamespace(payload=P), HS)
    new = chain([11, 12])                                    # complete chain ending with an A field
    p.insert_at(len(m0), new)
    out = p.rebuild()
    q = wlpart.Partition(types.SimpleNamespace(payload=bytes(out)), HS)
    raws = [bytes(m['raw']) for m in q.mem]
    assert blob in raws, 'the kept member was altered'
    k = raws.index(blob)
    assert raws[k - 1].endswith(new[-4:]) and max(map(len, raws)) <= 131088
    # frame in front of the kept member describes the kept member (X1 0, X2 = its length), not its successor
    fr = q.gaps[k - 1]
    assert struct.unpack_from('<I', fr, 12)[0] == 0 and struct.unpack_from('<I', fr, 20)[0] == len(blob)
