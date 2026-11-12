#!/usr/bin/env python3
"""rvt_split_oversize.py: LAB/EXPERIMENT. Revit 2026 caps partition members at 131,088 B raw. A single record larger than that is stored cut in two members:
first part 131,088 B (frame X1=1, X2=0x20000, marker word [8]=6), continuation (X1=0, X2=len-4, marker 5); the frames around keep marker 4.
Our writer merged such a record into ONE oversize member (238,572 B in the 2026 Structural sample) and Revit refused the file ('needs to be repaired'); cutting it like
this made Revit 2026 open it (VM y12, 2026-11-12). Works on a wlpart.Partition (write-lab) before save. Only the one-cut case (member <= 2*131,088) is handled; anything else raises."""
import struct
CAP = 131088
def split_oversize(pt):
    """pt: wlpart.Partition. Cuts every member above CAP once. Returns the list of cut member indexes (in the new numbering of the first part)."""
    pt.LIMIT = 10 ** 9                       # stop the writer's own cascade from touching these members
    cuts = []; k = 0
    while k < len(pt.mem):
        raw = bytes(pt.mem[k]['raw'])
        if len(raw) > CAP:
            if len(raw) > 2 * CAP: raise ValueError('member %d has %d B: more than one cut needed (not implemented)' % (k, len(raw)))
            if k < 2 or k + 1 >= len(pt.mem) - 1: raise ValueError('oversize member at the partition edge (not implemented)')
            pt.add_member_after(k)
            pt.mem[k]['raw'] = bytearray(raw[:CAP]); pt.mem[k + 1]['raw'] = bytearray(raw[CAP:])
            for q in (k, k + 1): pt.mem[q]['dirty'] = True
            pt.mem[k]['x1set'] = 1; pt.mem[k]['x2'] = 0x20000
            pt.mem[k + 1]['x1set'] = 0; pt.mem[k + 1]['x2'] = len(raw) - CAP - 4
            for idx, v in ((k - 2, 4), (k - 1, 6), (k, 5), (k + 1, 4)):      # frame before member i is gaps[i-1]; after add_member_after the indexes are as in the final numbering
                pt.gaps[idx][8:12] = struct.pack('<I', v)
            cuts.append(k); k += 2
        else: k += 1
    return cuts
