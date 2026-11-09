#!/usr/bin/env python3
"""rvt_dit_episode.py: model of Revit's Global/DocumentIncrementTable change on a save (new episode), derived from 28 Revit-made base->after pairs
(Autodesk samples only). dit_next(x, now) -> new bytes. Self-test: python3 rvt_dit_episode.py BASE.rvt AFTER.rvt compares with Revit's result
(timestamp word excluded). Offline model only; not wired into any save path."""
import struct, sys
U = struct.Struct('<I')
def _name_words(n): return 1 + (2 * n + 2 + 3) // 4
def _rec_len(n): return 4 * (3 + _name_words(n) + 18) + 1
def _recs(x):
    """offsets of 'count 1' episode records (1, ffffffff, id, nchars, name UTF-16, epA, epB, 0, time, save, id, 10 counters, ffffffff, last + 1 B):
    the saving user's name is arbitrary ('User' in later saves, e.g. a login name in an ORIGINAL file)"""
    out = []
    pat = b'\x01\x00\x00\x00\xff\xff\xff\xff'
    i = x.find(pat)
    while i >= 0:
        n = U.unpack_from(x, i + 12)[0] if i + 16 <= len(x) else 0
        if 1 <= n <= 40 and i + _rec_len(n) + 4 <= len(x):
            nm = x[i+16:i+16+2*n]
            try: ok = nm.decode('utf-16le').isprintable() and x[i+16+2*n:i+16+2*n+2] == b'\0\0'
            except Exception: ok = False
            if ok: out.append(i)
        i = x.find(pat, i+1)
    return out
def _name_block(name):
    nb = struct.pack('<I', len(name.encode('utf-16le')) // 2) + name.encode('utf-16le') + b'\0\0'
    return nb + b'\0' * (-len(nb) % 4)
def top_epb(x):
    """newest epB among the episode records (the file's current episode EP)"""
    return max(U.unpack_from(x, r + 12 + 4 * _name_words(U.unpack_from(x, r+12)[0]) + 4)[0] for r in _recs(x))
def top_counters(x):
    """the 10 episode counters + the last word (11 values) of the newest record (first copy)"""
    recs = _recs(x); nw = lambda r: _name_words(U.unpack_from(x, r+12)[0])
    epb = lambda r: U.unpack_from(x, r + 12 + 4 * nw(r) + 4)[0]
    r = [q for q in recs if epb(q) == max(epb(t) for t in recs)][0]
    return list(struct.unpack_from('<10I', x, r + 12 + 4 * nw(r) + 24)) + list(struct.unpack_from('<I', x, r + 12 + 4 * nw(r) + 24 + 44))
def dit_next(x, now, drows=0, newname=None):
    """newname: name of the saving user for the NEW record; default = the superseded record's own name (Revit-saved files: 'User').
    ORIGINAL files: pass the saving user's name (Revit wrote 'User' in the VM)."""
    recs = _recs(x)
    nwords = lambda r: _name_words(U.unpack_from(x, r+12)[0])
    epb = lambda r: U.unpack_from(x, r + 12 + 4 * nwords(r) + 4)[0]
    best = max(epb(r) for r in recs)           # newest epB
    tops = [r for r in recs if epb(r) == best]
    assert len(tops) == 2, 'expected the mirrored pair, got %d' % len(tops)
    y = bytearray(x); y[2] = (y[2] + 1) & 255
    for r in sorted(tops, reverse=True):
        nw = nwords(r); L = _rec_len(U.unpack_from(x, r+12)[0]); T = U.unpack_from(x, r+L)[0]
        hdr = list(struct.unpack_from('<3I', x, r)); nameb = bytes(x[r+12:r+12+4*nw])
        rest = list(struct.unpack_from('<18I', x, r+12+4*nw)); tail = bytes(x[r+L-1:r+L])
        # new record
        nr = rest[:]; nr[0] = rest[1]; nr[1] = rest[1] + 1; nr[3] = now; nr[4] = rest[4] + 1; nr[5] += drows
        for k in range(6, 16): nr[k] += 1
        nr[17] += 1
        nb = struct.pack('<3I', 1, 0xffffffff, hdr[2] + drows) + (_name_block(newname) if newname else nameb) + struct.pack('<18I', *nr) + tail
        # superseded record: count+1, (save,0) inserted after the id, its trailing id word zeroed
        orr = rest[:]; orr[5] = 0
        ob = struct.pack('<3I', hdr[0] + 1, hdr[1], hdr[2]) + struct.pack('<2I', rest[4], 0) + nameb + struct.pack('<18I', *orr) + tail
        y[r:r+L+4] = ob + nb + U.pack(T + 1 if r == min(tops) else T)      # only the first copy's trailer is the save counter
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
