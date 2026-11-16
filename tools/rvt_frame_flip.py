#!/usr/bin/env python3
"""rvt_frame_flip.py SRC PARTITION MEMBER FIELD DEST: copy SRC to DEST and add +1 to one frame field of one gzip member (FIELD = X1 | stored | X2 | after), page ECC re-stamped
(segedit.new_stream_pages), so only the structural rules of the gate can notice (c4x-rvtmatrix 2026-11-16, item 193). Local use: public Autodesk samples only."""
import os, sys, struct, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import segedit


def flip(src, part, k, fld, dest):
    s = segedit.Session(src, part=part); sp = s.sp; o = 24 if k == 0 else 12
    if fld == 'after': aa, ab = sp.frame_after(k); off = aa + 2; old = bytes(ab[2:6])
    else: fa, fb = sp.frame_before(k); i = {'X1': 0, 'stored': 4, 'X2': 8}[fld]; off = fa + o + i; old = bytes(fb[o + i:o + i + 4])
    new = struct.pack('<I', (struct.unpack('<I', old)[0] + 1) & 0xffffffff)
    pages = list(s.new_stream_pages([(off, 4, new)], 0))
    shutil.copyfile(src, dest); fd = os.open(dest, os.O_RDWR)
    try:
        for p, b in pages: segedit._pwrite_stream(fd, sp, p * segedit.PAGE_STORED, b)
    finally: os.close(fd)
    return dest


if __name__ == '__main__':
    src, part, k, fld, dest = sys.argv[1:6]; print(flip(src, part, int(k), fld, dest))
