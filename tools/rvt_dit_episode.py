#!/usr/bin/env python3
"""rvt_dit_episode.py: model of Revit's Global/DocumentIncrementTable change on a save (new episode), derived from 28 Revit-made base->after pairs
(Autodesk samples only). dit_next(x, now) -> new bytes. Self-test: python3 rvt_dit_episode.py BASE.rvt AFTER.rvt compares with Revit's result
(timestamp word excluded). Offline model only; not wired into any save path."""
import struct, sys
U = struct.Struct('<I')
def _recs(x):
    """offsets of 'User' episode records that are in the 'count 1' shape: 1, ffffffff, id, 4, 'User\\0'(12B), epA, epB, 0, time, save, id, 10 counters, ffffffff, last"""
    out = []
    pat = b'\x01\x00\x00\x00\xff\xff\xff\xff'
    i = x.find(pat)
    while i >= 0:
        if x[i+12:i+16] == b'\x04\x00\x00\x00' and x[i+16:i+24] == 'User'.encode('utf-16le'):
            out.append(i)
        i = x.find(pat, i+1)
    return out
RECLEN = 101
def dit_next(x, now, drows=0):
    recs = _recs(x)
    best = max(U.unpack_from(x, r+32)[0] for r in recs)           # newest epB
    tops = [r for r in recs if U.unpack_from(x, r+32)[0] == best]
    assert len(tops) == 2, 'expected the mirrored pair, got %d' % len(tops)
    y = bytearray(x); y[2] = (y[2] + 1) & 255
    for r in sorted(tops, reverse=True):
        old = bytes(x[r:r+RECLEN]); T = U.unpack_from(x, r+RECLEN)[0]       # record = 25 words + 1 byte, then a u32 trailer (save counter)
        w = list(struct.unpack('<25I', old[:100])); tail = old[100:]
        n = w[:]
        n[7] = w[8]; n[8] = w[8] + 1; n[10] = now; n[11] = w[11] + 1; n[2] += drows; n[12] += drows      # ids = ElemTable row count (delta == row delta, 28/28 pairs)
        for k in range(13, 23): n[k] += 1
        n[24] += 1
        nb = struct.pack('<25I', *n) + tail
        o = w[:]; o[0] += 1; o[12] = 0      # the superseded record loses its trailing user-id word
        ob = struct.pack('<3I', *o[:3]) + struct.pack('<2I', w[11], 0) + struct.pack('<22I', *o[3:]) + tail
        y[r:r+RECLEN+4] = ob + nb + U.pack(T + 1 if r == min(tops) else T)      # only the first copy's trailer is the save counter
    return bytes(y)
if __name__ == '__main__':
    sys.path[:0] = ['~/rvt-research/write-lab', '~/rvt-research']
    import adiff
    a, b = sys.argv[1:3]
    x = adiff.graw(a, 'Global/DocumentIncrementTable'); y = adiff.graw(b, 'Global/DocumentIncrementTable')
    p = dit_next(x, 0)
    ok = len(p) == len(y) and all(p[i] == y[i] for i in range(len(y)))
    if not ok:
        d = [i for i in range(min(len(p), len(y))) if p[i] != y[i]]
        print('DIFF len', len(p), len(y), 'first', d[:12])
        # tolerate only timestamp words
    print('EXACT' if ok else 'MISMATCH')
