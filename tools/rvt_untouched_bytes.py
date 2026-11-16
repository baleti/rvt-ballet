#!/usr/bin/env python3
"""rvt_untouched_bytes.py SRC OUT: byte-equality proof for the partitions an edit changed (c4x-rvtmatrix item 198, closes the item 196/197 gaps on the checking side).
For every Partitions/* stream whose bytes differ, align the gzip members by index and require: same member count; head, tail (up to zero slack) and every frame/interlude byte equal to the
source, except (a) the bytes of members whose compressed bytes differ (the dirty ones) and (b) their declared frame fields: before-frame X1/stored/X2 (frame offsets 12..23, member 0: head 24..35)
and the previous member's after-frame length (offsets 2..5 of the 32 bytes before the next member). Everything else must be identical.
--allow-streams=A,B: streams (e.g. ElemTable) an add/delete may rewrite; any other non-partition stream that differs is a violation ('_other_streams_changed').
--count-change: an add/delete op may change the head element count (u32 at payload offset 14).
Prints one JSON line: {partition: {members, dirty, violations: [payload offsets...], structure_changed}}; exit 1 on any violation or structure change. Public samples only."""
import os, sys, json
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab'))
import cfb, rvtw


def check_partition(pa, pb, count_change=False):
    ma = rvtw.members(pa, pa.find(rvtw.GZ)); mb = rvtw.members(pb, pb.find(rvtw.GZ))
    if len(ma) != len(mb): return dict(structure_changed='member count %d -> %d' % (len(ma), len(mb)))
    dirty = [k for k, ((sa, ea, _), (sb, eb, _)) in enumerate(zip(ma, mb)) if pa[sa:ea] != pb[sb:eb]]
    allowed = []      # (start, end) in SOURCE-frame segment coordinates handled per segment below
    viol = []
    def cmp(a, b, base, skip):
        if len(a) != len(b): viol.append(base); return
        for i in range(len(a)):
            if a[i] != b[i] and not any(s <= i < e for s, e in skip): viol.append(base + i)
    first = ma[0][0]; cmp(pa[:first], pb[:mb[0][0]], 0, ([(24, 36)] if 0 in dirty else []) + ([(14, 18)] if count_change else []))      # head u32 at +14 = element count of the partition: only an add/delete may change it (--count-change)
    pea, peb = ma[0][1], mb[0][1]
    for k in range(1, len(ma)):
        sa, ea, _ = ma[k]; sb, eb, _ = mb[k]; skip = []
        if k in dirty: skip.append((12, 24))
        if k - 1 in dirty: skip.append((2, 6))
        cmp(pa[pea:sa], pb[peb:sb], pea, skip); pea, peb = ea, eb
    ta, tb = pa[pea:], pb[peb:]
    if ta.rstrip(b'\0') != tb.rstrip(b'\0'): viol.append(pea)
    return dict(members=len(ma), dirty=len(dirty), violations=viol[:20], n_violations=len(viol))


def main(src, out, count_change=False, allow=()):
    A = cfb.CFB(open(src, 'rb').read()).streams(); B = cfb.CFB(open(out, 'rb').read()).streams(); res = {}
    other = sorted(n for n in set(A) | set(B) if not n.startswith('Partitions/') and (n not in A or n not in B or A[n].data != B[n].data) and n not in allow)
    if other: res['_other_streams_changed'] = dict(streams=other, n_violations=len(other))      # stream rule (item 201): outside the edited partitions nothing may differ unless the op legitimately rewrites it (--allow-streams)
    for n in A:
        if not n.startswith('Partitions/') or n not in B or A[n].data == B[n].data: continue
        pa = bytes(rvtw.Stream(A[n].data).payload); pb = bytes(rvtw.Stream(B[n].data).payload); res[n] = check_partition(pa, pb, count_change)
    bad = any(v.get('structure_changed') or v.get('n_violations') for v in res.values())
    print(json.dumps(res)); return 1 if bad else 0


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]; al = [x.split('=', 1)[1].split(',') for x in sys.argv if x.startswith('--allow-streams=')]; sys.exit(main(a[0], a[1], '--count-change' in sys.argv, tuple(al[0]) if al else ()))
