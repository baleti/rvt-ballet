#!/usr/bin/env python3
"""elemtable_rule.py FILE... : check the exact length rule of the decompressed Global/ElemTable (observed on 10 of 11 sample files 2011_2..2022:
len == 6 + 28*count + 19, count = u32 at offset 2). Prints OK/BREAK/OTHER (other = layout without the rule, e.g. 2011_1). A BREAK on a saved output
is a candidate cheap gate check (a truncated or padded table). Needs numpy + ~/rvt-research/write-lab. Aggregate output only."""
import sys, os, struct, zlib
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import cfb, rvtw
LAYOUTS = [(28, 19), (40, 24)]      # (row width, tail) seen: 2011_2..2022 = 28+19; 2024/2026 = 40+24 (to be confirmed on the unedited samples)
def check(path):
    s = cfb.CFB(open(path, 'rb').read()).streams()['Global/ElemTable']
    P = bytes(rvtw.Stream(s.data).payload); D = zlib.decompressobj(31).decompress(P[P.find(rvtw.GZ):])
    n = struct.unpack('<I', D[2:6])[0]
    for w, t in LAYOUTS:
        if len(D) == 6 + w * n + t: return 'OK/%d+%d' % (w, t), len(D), n
    near = [w for w, t in LAYOUTS if abs(len(D) - 6 - w * n - t) <= 4096]
    return ('BREAK' if near else 'OTHER'), len(D), n
if __name__ == '__main__':
    for p in sys.argv[1:]:
        try: print(os.path.basename(p)[:14], *check(p))
        except Exception as e: print(os.path.basename(p)[:14], 'ERR', repr(e)[:60])
