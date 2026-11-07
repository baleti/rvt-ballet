"""Regression: rvt-ballet's CachedRvtAdapter.extra_checks must INHERIT savegate's dirty_members rule (it shadowed it, so an undeclared flip in a partition member passed the gate; found by tools/rvt_changetype_flip.py, 4 of 8 flips escaped).
Checks on the 5 MB Autodesk 2024 template: with dirty_members declared, a flipped byte inside a partition member that is NOT declared is reported; declaring every differing member (or no flip) gives no finding. Skips when the sample is absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
SRC = os.environ.get('DM_FILE') or os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
from rvtballet import save
ad = save._cached_adapter()(); b = open(SRC, 'rb').read(); n = len(b)
ad._verify_bufs = (b, b); assert ad.extra_checks({'dirty_members': {'Partitions/21': [0]}}) == [], 'identity must give no finding'
found = None
for k in range(1, 200):
    o = n // 3 + k * 40009; x = bytearray(b); x[o] ^= 1; ad._verify_bufs = (b, bytes(x)); r = ad.extra_checks({'modified': [], 'dirty_members': {}})
    if any(f[0] == 'dirty_members' and 'not declared' in f[1] for f in r): found = (o, bytes(x), r); break
assert found, 'no flip landed in a partition member within 60 tries (adjust the probe)'
o, x, r = found; print('flip at', o, '->', str(r)[:160])
import re; idx = [int(i) for i in re.findall(r'members \[([0-9, ]+)\]', r[0][1])[0].split(',')]; pn = re.match(r'(Partitions/\d+)', r[0][1]).group(1)
ad._verify_bufs = (b, x); assert ad.extra_checks({'modified': [], 'dirty_members': {pn: idx}}) == [], 'declaring the differing members must pass'
print('dirty_members adapter OK')
