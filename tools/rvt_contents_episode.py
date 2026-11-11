#!/usr/bin/env python3
"""rvt_contents_episode.py: offline model of Revit's 'Contents' stream change on a save: header episode byte +1 (@87 if the plain header is 91 B, @20 if 24 B),
gzip payload (240 B raw): u32 counters at raw offsets 156,160,...,188 and 196 each +1 (low byte; verified 28/28 as a +1 on the byte). Self-test vs Revit pairs."""
import sys, zlib, struct
OFFS = (156, 160, 164, 168, 172, 176, 180, 184, 188, 196)
def contents_next(x, counters=None):
    """counters: the 10 u32 counters of the newest DIT episode record BEFORE the save. In ORIGINAL files the payload is shifted, so the 9+1 counters are located by value
    (9 u32 = counters minus index 7, then ffffffff, then the DIT record's last word); without it the fixed offsets of Revit-saved files are used."""
    x = bytes(x); i = x.find(b'\x1f\x8b\x08'); assert i in (24, 91), 'unexpected Contents header size %d' % i
    raw = bytearray(zlib.decompressobj(31).decompress(x[i:]))
    offs = OFFS
    if counters is not None:      # counters = the DIT record's 10 counters + its last word (11 values); Contents holds counters minus index 7, then ffffffff, then the last word
        c9 = [v for j, v in enumerate(counters[:10]) if j != 7]
        pat = struct.pack('<9I', *c9) + b'\xff\xff\xff\xff' + struct.pack('<I', counters[10]); k = bytes(raw).find(pat)
        assert k >= 0 and bytes(raw).find(pat, k + 1) < 0, 'counter run not found (or ambiguous) in Contents payload'
        offs = [k + 4 * j for j in range(9)] + [k + 40]
    for o in offs:
        v = struct.unpack_from('<I', raw, o)[0]; struct.pack_into('<I', raw, o, v + 1)
    hdr = bytearray(x[:i]); hdr[87 if i == 91 else 20] += 1
    sys.path[:0] = ['~/rvt-research/write-lab', '~/rvt-research']
    import rvtw      # write-lab: deflate_to_size makes a valid deflate stream of EXACTLY the original length (the stream keeps Revit's size)
    # c4x 2026-11-11 (VM verdict z_c): padding the deflate with empty sync blocks to fill the slot made Revit 2026 say 'saved by a later version'. Revit writes a COMPACT
    # deflate and leaves the rest of the slot as it was; do the same: shortest raw deflate that fits, then keep the old slot bytes behind the gzip trailer.
    cand = []
    for lvl in (9, 6, 1):
        c = zlib.compressobj(lvl, zlib.DEFLATED, -15); cand.append(c.compress(bytes(raw)) + c.flush())
    z = min(cand, key=len)
    assert len(z) + 10 + 8 <= len(x) - i, 'compact deflate does not fit the Contents slot'
    gz = x[i:i+10] + z + struct.pack('<II', zlib.crc32(bytes(raw)) & 0xffffffff, len(raw))
    gz = gz + x[i + len(gz):]
    return bytes(hdr) + gz
if __name__ == '__main__':
    sys.path[:0] = ['~/rvt-research/write-lab', '~/rvt-research']
    import adiff
    a, b = sys.argv[1:3]; x = adiff.graw(a, 'Contents'); y = adiff.graw(b, 'Contents'); p = contents_next(x)
    ra = zlib.decompressobj(31).decompress(p[p.find(b'\x1f\x8b\x08'):]); rb = zlib.decompressobj(31).decompress(y[y.find(b'\x1f\x8b\x08'):])
    hi = p.find(b'\x1f\x8b\x08')
    print('EQUIVALENT (same length, same header, same decompressed payload)' if len(p) == len(y) and p[:hi] == y[:hi] and ra == rb else 'MISMATCH len %d/%d' % (len(p), len(y)))
