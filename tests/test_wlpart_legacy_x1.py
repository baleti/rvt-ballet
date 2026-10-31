"""c5x-rvtwrite2: in a legacy (2017/2018 style, record size 12) partition the record-chain walk does not reproduce the file's own X1 for a member;
a size-changing edit used to overwrite X1 with the walk count (2017 Comments edit => Revit CorruptModelException). The file's own X1 must be kept
unless the walk reproduces it on the original bytes. Synthetic data only."""
import os, sys, struct, zlib, types, pytest
WL = os.path.expanduser('~/rvt-research/write-lab')
if not os.path.isdir(WL): pytest.skip('rvt-research write-lab not present', allow_module_level=True)
sys.path.insert(0, WL)
import wlpart, rvtw

HS = 12

def chain(sizes):
    """records of header HS whose last 4 header bytes hold the following data length, so the walk in wlpart steps record to record"""
    b = bytearray(); 
    for n in sizes:
        b += b'\0' * (HS - 4) + struct.pack('<I', n) + b'\1' * n
    return bytes(b)

def gz(raw):
    c = zlib.compressobj(9, zlib.DEFLATED, -15); d = c.compress(raw) + c.flush()
    return rvtw.GZ + b'\0' * 6 + d + struct.pack('<II', zlib.crc32(raw), len(raw))

def partition(raws, x1s):
    P = bytearray(b'\0' * 44)
    for k, raw in enumerate(raws):
        if k:
            gap = bytearray(32)
            P += gap
            struct.pack_into('<I', P, len(P) - 32 + 12, x1s[k]); struct.pack_into('<I', P, len(P) - 32 + 20, len(raw) - HS * x1s[k])
        else:
            struct.pack_into('<I', P, 24, x1s[0]); struct.pack_into('<I', P, 32, len(raw) - HS * x1s[0])
        P += gz(raw)
    return wlpart.Partition(types.SimpleNamespace(payload=bytes(P)), 16)

def grow(p):
    m = p.mem[0]; m['raw'] += b'\2' * 8; m['dirty'] = True; m['delta'] += 8
    p.cascade()
    return m

def test_legacy_keeps_file_x1_when_walk_disagrees():
    raw = chain([30, 40, 50])
    stored = 5                                  # what the file says; the chain walk gives fewer
    p = partition([raw, chain([3])], [stored, 1])
    assert p.legacy
    m = grow(p)
    assert 'x1set' not in m, 'legacy member whose stored X1 the walk cannot reproduce got a recomputed X1'

def test_legacy_uses_walk_when_it_reproduces_x1():
    raw = chain([30, 40, 50])
    for walk in range(1, 6):                      # find the X1 value the walk itself yields on this chain
        p = partition([raw, chain([3])], [walk, 1])
        if p._walk_ok(p.mem[0]): break
    else: pytest.fail('no X1 reproduces on the synthetic chain')
    m = p.mem[0]
    grow(p)
    assert 'x1set' in m
