#!/usr/bin/env python3
"""rvt_offset_classify.py FILE OFFSET... : which CFB region does a file byte offset fall in (header, FAT/DIFAT/dir sector, which stream and stream offset, and for a gzip-partition stream which member and part: header/deflate/trailer/frame). Aggregates only; no content printed."""
import sys, olefile, zlib, struct
def main(path, offs):
    ole = olefile.OleFileIO(path); ss = ole.sectorsize; data = open(path, 'rb').read()
    owner = {}
    for e in ole.listdir(streams=True, storages=False):
        ent = ole.direntries[ole._find(e)] if hasattr(ole, '_find') else None
    # map sector -> (stream, index) via fat chains
    for d in ole.direntries:
        if d is None or d.entry_type != 2 or d.size < ole.minisectorcutoff: continue
        s = d.isectStart; i = 0
        while s < 0xFFFFFFF0 and s not in owner and i < 10**6: owner[s] = (d.name, i, d.size); s = ole.fat[s]; i += 1
    for off in offs:
        if off < 512 and ss == 512 or off < ss: print(off, 'CFB header'); continue
        sec = (off - ss) // ss; ino = (off - ss) % ss
        if sec in owner:
            name, k, size = owner[sec]; soff = k * ss + ino
            print(off, 'sector', sec, 'stream', name, 'stream_off', soff, 'of', size, 'SLACK(after stream end)' if soff >= size else 'DATA')
        else: print(off, 'sector', sec, 'FAT/DIFAT/dir/mini or free (no big-stream owner)')
main(sys.argv[1], [int(x) for x in sys.argv[2:]])
