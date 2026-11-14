#!/usr/bin/env python3
"""rvt_rec_bytediff.py BEFORE.rvt AFTER.rvt EID [EID..]: slice each element's OWN record bytes (same walk as rvt_diff/recwalk) and print the byte offsets that differ,
with hex context and the field the reader places there (when known). For records rvt_diff reports as 'changed' with no decoded field diff (undecoded regions).
Autodesk samples / synthetic only; offline."""
import sys, os, struct
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
import wledit


def records(path, want):
    m = wledit.Editor(path).m; W = m.IDW; hs = 12 + W; EHT = struct.pack('<H', m.sch.by['ElementHeader'] + 12); out = {}
    for pn, p in m.parts.items():
        bj = p['joined']; n = len(bj); q = 0
        while q + W + 6 <= n and bj[q + W + 4:q + W + 6] == EHT:
            Lh = struct.unpack_from('<I', bj, q + W)[0]; q += W + 4 + Lh + 4
        q -= 4
        while q + hs <= n:
            L = struct.unpack_from('<I', bj, q + 4 + W + 4)[0]; i = int.from_bytes(bj[q + 4:q + 4 + W], 'little')
            if q + hs + L > n + 4: break
            if i in want: out.setdefault(i, []).append(bytes(bj[q + 4:q + hs + L]))
            q += hs + L
    return out, m


def main():
    a, b, ids = sys.argv[1], sys.argv[2], {int(x) for x in sys.argv[3:]}
    ra, ma = records(a, ids); rb, mb = records(b, ids)
    for eid in sorted(ids):
        xs, ys = ra.get(eid, []), rb.get(eid, [])
        print('id %d: records before %d (%s B) after %d (%s B)' % (eid, len(xs), [len(x) for x in xs], len(ys), [len(y) for y in ys]))
        for k, (x, y) in enumerate(zip(xs, ys)):
            d = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
            print('  record %d: %d differing bytes%s' % (k, len(d), (' at ' + ','.join(map(str, d[:24]))) if d else ''))
            for i in d[:8]: print('    %d: %s -> %s' % (i, x[max(0, i - 4):i + 8].hex(), y[max(0, i - 4):i + 8].hex()))


if __name__ == '__main__': main()
