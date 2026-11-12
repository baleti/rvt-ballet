#!/usr/bin/env python3
"""rvt_ep_stamp.py: LAB/EXPERIMENT. Partition-header episode stamps of a Revit 2026 save, derived from the Structural pair (c4xaw26, ours vs Revit's after).
Rule (VM-verified only together with Revit's other bytes, see c3x-progress 2026-11-12): the partition begins with 22-byte entries (from offset 14) whose first u32 'A' is the
save-episode number that last touched them. In the saved base every entry from k=1 on holds old EP (0x426); Revit's next save writes new EP (0x427) into all of them.
So: for entries k=1..N at 14+22k, if A == old_ep then A := new_ep. (EP is the DIT top record's epB, see rvt_new_episode.py.)
NOT covered yet: the +1/-1 byte pairs near offsets 360 and 5591297, the record flag 0x1f->0x1e and the Adler32 of the 6884 B chunk (see RVT-PATTERNS.md)."""
import struct
def stamp_entries(part, old_ep, new_ep, first=1, limit=64):
    part = bytearray(part); n = 0
    for k in range(first, limit):
        o = 14 + 22 * k
        if o + 4 > len(part): break
        if struct.unpack_from('<I', part, o)[0] == old_ep:
            struct.pack_into('<I', part, o, new_ep); n += 1
    return bytes(part), n

def fix_chunk(part, s):
    """Wall-record chunk header at partition offset s (c4xaw26: 37436623): u32 adler at s+8, u32 body length at s+12, body at s+16, flag byte at s+18 relative to
    the start of the 11 B field after the wall id (read from run 15 of the Structural pair: adler 4 B | len 4 B | 9e 08 | flag). VM-verified (x_w2) with flag 0x1f->0x1e
    and the adler recomputed over the body: Revit accepts. Returns new bytes."""
    import zlib
    part = bytearray(part)
    n = struct.unpack_from('<I', part, s + 12)[0]
    assert 0 < n < 1 << 20 and s + 16 + n <= len(part), 'chunk length implausible'
    if part[s + 18] == 0x1f: part[s + 18] = 0x1e
    struct.pack_into('<I', part, s + 8, zlib.adler32(bytes(part[s + 16:s + 16 + n])) & 0xffffffff)
    return bytes(part)

def find_chunks(part, limit=64):
    """Self-validating scan for wall chunk headers: ... adler(4) len(4) 9e 08 1f ...  where adler32(part[s+16:s+16+len]) == stored adler.
    Returns the list of chunk header offsets s (chunk header = 8 B before the adler field; fix_chunk(part, s))."""
    import zlib
    out = []; pat = b'\x9e\x08\x1f'; i = part.find(pat)
    while i >= 0 and len(out) < limit:
        s = i - 16                      # body starts at s+16 with 9e 08 1f
        if s >= 0:
            n = struct.unpack_from('<I', part, s + 12)[0]
            if 0 < n < 1 << 20 and s + 16 + n <= len(part) and struct.unpack_from('<I', part, s + 8)[0] == zlib.adler32(part[s + 16:s + 16 + n]) & 0xffffffff:
                out.append(s)
        i = part.find(pat, i + 1)
    return out
