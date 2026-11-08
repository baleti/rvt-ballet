"""Offline dangling-reference check for a delete output: ids that exist in ORIG but not in OUT must not be mentioned (as a whole number) in the decoded parameters of any surviving element of OUT, unless ORIG already had that mention from a non-existent target.
usage: tools/rvt_dangling_check.py ORIG OUT   (prints aggregate counts and class names only; exit 1 if dangling refs found). Params only: header/ref fields not shown as parameters are not covered."""
import os, sys, re, collections
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
import rvt_params
a = rvt_params.params(sys.argv[1]); b = rvt_params.params(sys.argv[2])
gone = set(a) - set(b)
if not gone: print('no ids removed'); sys.exit(0)
num = re.compile(r"(?<=: )(\d{2,12})(?=[,}\]])|(?<=, )(\d{2,12})(?=[,}\]])")      # numeric VALUES only (not digits inside GUIDs/names)
cl = collections.Counter(); hits = 0
for e, d in b.items():
    for m in set(x for t in num.findall(repr(d)) for x in t if x):
        v = int(m)
        if v in gone and v != e: hits += 1; cl[(a[v].get('class') if isinstance(a[v], dict) else '?', d.get('class') if isinstance(d, dict) else '?')] += 1
print('removed ids', len(gone), 'dangling mentions', hits, 'by (removed class, holder class):', dict(cl.most_common(8)))
sys.exit(1 if hits else 0)
