"""gzcheck: integrity walk over the gzip members of a Revit partition stream (Partitions/N payload).
Revit partitions hold consecutive gzip members (10-byte header 1f8b0800.., raw deflate, CRC32+ISIZE trailer) separated by 32-byte frames.
member_report(payload) -> (members_seen, [index of every member that inflates but whose CRC32/ISIZE trailer does not match], stop_index).
stop_index is the index of the first member the walk could not inflate (layout end OR a damaged deflate stream; the two cannot be told apart here), or None.
Walks while the next member starts right after the 32-byte frame; it stops (does not guess) where that layout ends, so it is a lower bound:
members it never reaches are NOT reported. Evidence for the need: a flipped deflate byte (2 payload bytes changed) is accepted and carried by an
edited SAVE AS today (c7x-rvtwrite 2026-11-01); not wired into save.py yet (decision for the owner)."""
import zlib, struct
GZ = b'\x1f\x8b\x08\x00'


def member_report(payload, start=None):
    pos = payload.find(GZ) if start is None else start
    seen = 0; bad = []; stop = None
    while pos >= 0 and pos + 18 <= len(payload) and payload[pos:pos + 4] == GZ:
        do = zlib.decompressobj(-15)
        try: raw = do.decompress(payload[pos + 10:])
        except zlib.error: stop = seen; break          # cannot find the member end: stop, the rest is unreachable
        if not do.eof: stop = seen; break
        end = len(payload) - len(do.unused_data) + 8
        if end > len(payload): stop = seen; break
        crc, isz = struct.unpack('<II', payload[end - 8:end])
        if crc != (zlib.crc32(raw) & 0xffffffff) or isz != (len(raw) & 0xffffffff): bad.append(seen)
        seen += 1; pos = end + 32
    return seen, bad, stop
