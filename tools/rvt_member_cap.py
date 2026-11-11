"""Output sanity: Revit never writes a partition member with more than 131088 raw bytes (131 members of exactly 131088 in a 2026 base, none larger).
A writer output with a bigger member (c4x 2026 add: 238572 B = two members merged) is not a layout Revit produces; refuse it.
oversized(sizes) -> list of (index, size); max_member_sizes(path) reads a .rvt with the write-lab partition parser (None if unavailable)."""
import os, sys
CAP = 131088
def oversized(sizes, cap=CAP):
    return [(i, s) for i, s in enumerate(sizes) if s > cap]
def member_sizes(path):
    for p in ('~/rvt-research/write-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
    import cfb, rvtw, wlpart
    c = cfb.CFB(open(path, 'rb').read()); out = []
    for n in sorted(k for k in c.streams() if k.startswith('Partitions/')):
        out += [len(m['raw']) for m in wlpart.Partition(rvtw.Stream(c.streams()[n].data)).mem]
    return out
