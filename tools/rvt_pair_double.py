"""rvt_pair_double.py A B OLD NEW: for a Revit-made pair (A before, B after; .rvt/.rfa), report every place where the 8-byte little-endian double OLD in A's decompressed streams is NEW in B at the same offset (same stream, same length). Use to locate a numeric field changed through the Revit API (e.g. extrusion end offset 1.0 -> 2.5; note Revit stores lengths in feet, angles in radians). Read-only, Autodesk/synthetic files only.
Paged partition streams are read through rvtw.Stream(...).payload, other streams through rvtfmt.inflate_stream when they are gzip framed, else raw."""
import sys, os, struct
for p in ('~/rvt-research', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
import cfb, rvtw
def payloads(path):
    out = {}
    for n, e in cfb.CFB(open(path, 'rb').read()).streams().items():
        d = bytes(e.data)
        try: out[n] = bytes(rvtw.Stream(d).payload) if n.startswith('Partitions/') or n in ('Formats/Latest', 'Global/Latest') else d
        except Exception: out[n] = d
    return out
def find(a, b, old, new):
    ko, kn = struct.pack('<d', old), struct.pack('<d', new); hits = []
    for n in sorted(set(a) & set(b)):
        x, y = a[n], b[n]
        if len(x) != len(y): continue
        i = x.find(ko)
        while i != -1:
            if y[i:i + 8] == kn: hits.append((n, i))
            i = x.find(ko, i + 1)
    return hits
if __name__ == '__main__':
    A, B, o, n = sys.argv[1:5]; hs = find(payloads(A), payloads(B), float(o), float(n))
    for h in hs[:40]: print('%s +%d' % h)
    print(len(hs), 'hit(s)')
