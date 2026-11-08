#!/usr/bin/env python3
"""rvt_hdr_diff.py BEFORE.rvt AFTER.rvt [--show N]: raw ElementHeader byte diff (rvt_diff only reports header_changed via md5).
Prints how many headers differ, length changes, the byte offsets that change (count of elements per offset), the commonest old->new byte pairs,
and the first N element headers in hex. Autodesk samples / synthetic only; offline."""
import sys, os, struct, collections
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
import wledit
def hdrs(path):
    m = wledit.Editor(path).m; W = m.IDW; EHT = struct.pack('<H', m.sch.by['ElementHeader'] + 12); out = {}
    for pn, p in m.parts.items():
        bj = p['joined']; n = len(bj); q = 0
        while q + W + 6 <= n and bj[q + W + 4:q + W + 6] == EHT:
            i = int.from_bytes(bj[q:q + W], 'little'); Lh = struct.unpack_from('<I', bj, q + W)[0]
            out[i] = bytes(bj[q:q + W + 4 + Lh]); q += W + 4 + Lh + 4
    return out
def main():
    a, b = hdrs(sys.argv[1]), hdrs(sys.argv[2]); show = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 1
    ch = sorted(i for i in a if i in b and a[i] != b[i])
    print('headers: before %d after %d; added %d removed %d; changed %d' % (len(a), len(b), len(set(b) - set(a)), len(set(a) - set(b)), len(ch)))
    print('length changes (old,new):', collections.Counter((len(a[i]), len(b[i])) for i in ch).most_common(4))
    off = collections.Counter(); vals = collections.Counter()
    for i in ch:
        x, y = a[i], b[i]
        if len(x) == len(y):
            for k in range(len(x)):
                if x[k] != y[k]: off[k] += 1; vals[(x[k], y[k])] += 1
    print('offsets (offset, n elements):', sorted(off.items())[:40]); print('byte pairs:', vals.most_common(8))
    for i in ch[:show]: print(i, 'old', a[i].hex()); print(i, 'new', b[i].hex())
main()
