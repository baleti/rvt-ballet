#!/usr/bin/env python3
"""rvt_target_check.py SRC.rvt OUT.rvt --target ID [--allow ID,..] [--delete]
Move/rotate/resize (default): no element added/removed, only target (+allowed) elements changed, partition length unchanged.
--delete: only target (+allowed) removed, none added, only target/allowed changed.
Exit 1 on any element outside the allowed set changing (severity 1 candidate). Autodesk samples / synthetic only."""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_diff
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out'); ap.add_argument('--target', type=int, required=True)
ap.add_argument('--allow', default=''); ap.add_argument('--delete', action='store_true'); a = ap.parse_args()
ok = {a.target} | {int(x) for x in a.allow.split(',') if x}
rep = rvt_diff.diff(a.src, a.out, False, maxrec=100000)
bad = []
def _i(r): return r if isinstance(r, int) else (r.get('id') if isinstance(r, dict) else r)
real_added = [r for r in rep['added'] if _i(r) < 2**32]    # ids >= 2^32 are walker misalignment artifacts (no sample has them)
def _et_ids(path):
    """ids listed in Global/ElemTable (row stride 40 B with 8-byte ids, 28 B with 4-byte ids); None if unreadable"""
    try:
        import struct; sys.path.insert(0, os.path.expanduser('~/rvt-research/edit-lab')); sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
        import rvtedit; g = rvtedit.Edit(path).g; et = g._et(); n = struct.unpack_from('<I', et, 2)[0]
        S = min((x for x in (40, 28, 32, 36, 44) if 0 <= len(et) - 6 - n * x < 256), default=40 if g.W == 8 else 28)
        return {int.from_bytes(et[6 + S * k:6 + S * k + g.W], 'little') for k in range(n)}
    except Exception: return None
if real_added:       # an id the output ElemTable does not list (or the source already listed) is a walker misalignment id, not an added element
    _ea, _eb = _et_ids(a.src), _et_ids(a.out)
    if _ea is not None and _eb is not None: real_added = [r for r in real_added if _i(r) in _eb and _i(r) not in _ea]
art_added = len(rep['added']) - len(real_added)
if real_added: bad.append('%d elements added %s' % (len(real_added), real_added[:5]))
rem = {r if isinstance(r, int) else (r.get('id') if isinstance(r, dict) else r) for r in rep['removed']}
if a.delete:
    extra = [r for r in rep['removed'] if (r if isinstance(r, int) else (r.get('id') if isinstance(r, dict) else r)) not in ok]
    if extra: bad.append('removed outside allowed set: %s' % extra[:8])
    if a.target not in rem: bad.append('target not removed')
elif rep['n_removed']: bad.append('%d elements removed' % rep['n_removed'])
ch = [c['id'] for c in rep['changed'] if c.get('id') is not None]
stray = [i for i in ch if i not in ok]
if stray: bad.append('changed outside allowed set: %s' % stray[:8])
def _witness(path):
    try:
        sys.path.insert(0, os.path.expanduser('~/rvt-research/edit-lab')); sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
        import rvtedit
        return {l[1]: str(l[4]) for l in rvtedit.Edit(path).g.e.trace(a.target)[3] if l[1] in ('FamilyInstance.m_instOrigin', 'Trf.m_or', 'Trf.m_3x3')}
    except Exception: return None
_wit = None
if not a.delete and a.target not in ch:      # walker blind to the record (mesh-cached): fall back to the decoded origin/transform fields of the target
    _w0, _w1 = _witness(a.src), _witness(a.out)
    _wit = bool(_w0 and _w1 and _w0 != _w1)
    if _wit: ch = ch + [a.target]; print('note: target seen changed via trace witness (walker blind)')
if not a.delete and a.target not in ch: bad.append('UNVERIFIED: target not seen as changed (walker blind to this record or edit did not land)')
if not a.delete:
    for pn, d in rep['joined'].items():
        if d['len_old'] != d['len_new']: bad.append('%s length %d -> %d' % (pn, d['len_old'], d['len_new']))
def _positional():
    """equal-length partitions: byte-by-byte compare (exact, unlike the alignment diff) and require every differing byte inside the target's record span; returns (ok, n_diff_bytes, msg) or None"""
    try:
        import numpy as np
        sys.path.insert(0, os.path.expanduser('~/rvt-research/edit-lab')); sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
        import rvtedit, rvt_scan
        ea, eb = rvtedit.Edit(a.src), rvtedit.Edit(a.out); ma, mb = ea.g.e.m, eb.g.e.m; W = ea.g.W; tot = 0
        for pn, d in rep['joined'].items():
            if d['len_old'] != d['len_new']: return None
            x = np.frombuffer(ma.parts[pn]['joined'], np.uint8); y = np.frombuffer(mb.parts[pn]['joined'], np.uint8)
            diff = np.nonzero(x != y)[0]; tot += len(diff)
            if not len(diff): continue
            hs = sorted(int(i) for i in rvt_scan.header_candidates_tagged(ma.parts[pn]['joined'], ma.idarr, W, ma.etags))
            ids = {int.from_bytes(ma.parts[pn]['joined'][i + 4:i + 4 + W], 'little'): i for i in hs}
            if a.target not in ids: return None
            spans = []
            for t in ok:
                if t in ids: o = ids[t]; spans.append((o, min([h for h in hs if h > o] or [len(x)])))
            inside = np.zeros(len(diff), bool)
            for o, nx in spans: inside |= (diff >= o) & (diff < nx)
            out = diff[~inside]
            if len(out): return (False, tot, '%d differing bytes outside the target/allowed records %s in %s, first at %d' % (len(out), spans[:3], pn, out[0]))
        return (True, tot, '')
    except Exception: return None
if not a.delete and not bad:
    _pc = _positional()
    if _pc and not _pc[0]: bad.append(_pc[2])
    elif _pc: print('positional: %d differing bytes, all inside the target record' % _pc[1])
print('STRAY' if bad else 'CLEAN', '; '.join(bad[:6]) or 'target-only (%d changed, %d walker-artifact ids ignored, %d runs)' % (len(ch), art_added, sum(d['n_runs'] for d in rep['joined'].values())))
sys.exit(1 if bad else 0)
