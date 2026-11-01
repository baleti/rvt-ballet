#!/usr/bin/env python3
"""rvtwrite2_gzcheck.py FILE...: per file, walk the gzip members of every Partitions/* stream and verify CRC32+ISIZE. Prints aggregate ok/bad per file (short id only). Read-only measurement for a proposed member-integrity gate (false-positive rate on undamaged files)."""
import sys, os, zlib, struct, hashlib
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import cfb
GZ = b'\x1f\x8b\x08\x00'
def check(payload):
    ok = bad = 0; pos = payload.find(GZ)
    while pos >= 0 and pos + 10 <= len(payload):
        do = zlib.decompressobj(-15)
        try: raw = do.decompress(payload[pos+10:])
        except zlib.error: bad += 1; break
        if not do.eof: bad += 1; break
        end = len(payload) - len(do.unused_data)
        crc, isz = struct.unpack('<II', payload[end:end+8])
        if crc == zlib.crc32(raw) & 0xffffffff and isz == len(raw) & 0xffffffff: ok += 1
        else: bad += 1
        pos = end + 8 + 32
        if payload[pos:pos+4] != GZ: break
    return ok, bad
for f in sys.argv[1:]:
    c = cfb.CFB(open(f, 'rb').read()); tok = tbad = n = 0
    for name, e in c.streams().items():
        if name.startswith('Partitions/'): n += 1; o, b = check(c._read(e)); tok += o; tbad += b
    print(hashlib.sha1(os.path.basename(f).encode()).hexdigest()[:6], 'streams', n, 'members_ok', tok, 'bad', tbad, flush=True)
