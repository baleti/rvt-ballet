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
