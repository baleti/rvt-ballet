#!/usr/bin/env python3
"""rvt_contents_episode.py: offline model of Revit's 'Contents' stream change on a save: header episode byte +1 (@87 if the plain header is 91 B, @20 if 24 B),
gzip payload (240 B raw): u32 counters at raw offsets 156,160,...,188 and 196 each +1 (low byte; verified 28/28 as a +1 on the byte). Self-test vs Revit pairs."""
import sys, zlib, struct
OFFS = (156, 160, 164, 168, 172, 176, 180, 184, 188, 196)
def contents_next(x, level=None):
    x = bytes(x); i = x.find(b'\x1f\x8b\x08'); assert i in (24, 91), 'unexpected Contents header size %d' % i
    raw = bytearray(zlib.decompressobj(31).decompress(x[i:]))
    for o in OFFS:
        v = struct.unpack_from('<I', raw, o)[0]; struct.pack_into('<I', raw, o, v + 1)
    hdr = bytearray(x[:i]); hdr[87 if i == 91 else 20] += 1
    sys.path[:0] = ['~/rvt-research/write-lab', '~/rvt-research']
    import rvtw      # write-lab: deflate_to_size makes a valid deflate stream of EXACTLY the original length (the stream keeps Revit's size)
    z = rvtw.deflate_to_size(bytes(raw), len(x) - i - 18)
    assert z is not None, 'cannot reproduce the original deflate length'
    gz = x[i:i+10] + z + struct.pack('<II', zlib.crc32(bytes(raw)) & 0xffffffff, len(raw))
    return bytes(hdr) + gz
if __name__ == '__main__':
    sys.path[:0] = ['~/rvt-research/write-lab', '~/rvt-research']
    import adiff
    a, b = sys.argv[1:3]; x = adiff.graw(a, 'Contents'); y = adiff.graw(b, 'Contents'); p = contents_next(x)
    ra = zlib.decompressobj(31).decompress(p[p.find(b'\x1f\x8b\x08'):]); rb = zlib.decompressobj(31).decompress(y[y.find(b'\x1f\x8b\x08'):])
    hi = p.find(b'\x1f\x8b\x08')
    print('EQUIVALENT (same length, same header, same decompressed payload)' if len(p) == len(y) and p[:hi] == y[:hi] and ra == rb else 'MISMATCH len %d/%d' % (len(p), len(y)))
