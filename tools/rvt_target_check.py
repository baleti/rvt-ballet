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
if not a.delete and a.target not in ch: bad.append('UNVERIFIED: target not seen as changed (walker blind to this record or edit did not land)')
if not a.delete:
    for pn, d in rep['joined'].items():
        if d['len_old'] != d['len_new']: bad.append('%s length %d -> %d' % (pn, d['len_old'], d['len_new']))
print('STRAY' if bad else 'CLEAN', '; '.join(bad[:6]) or 'target-only (%d changed, %d walker-artifact ids ignored, %d runs)' % (len(ch), art_added, sum(d['n_runs'] for d in rep['joined'].values())))
sys.exit(1 if bad else 0)
