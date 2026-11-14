"""c3x-rvtlink: unload then reload of a multi-partition link type restores both partition copies' flag (2026 Electrical local sample, skipped if absent)."""
import os, sys, tempfile
SEED = os.path.expanduser('~/c5x-link/y2526b/e26_seed.rvt')
if not os.path.exists(SEED): print('SKIP'); sys.exit(0)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import rvtedit
from rvtballet import edit
d = tempfile.mkdtemp(); a = os.path.join(d, 'a.rvt'); b = os.path.join(d, 'b.rvt')
edit._apply_rvtedit(SEED, a, [{'op': 'set_link_load', 'eid': 1362427, 'value': 0}])
edit._apply_rvtedit(a, b, [{'op': 'set_link_load', 'eid': 1362427, 'value': 1}])
e = rvtedit.Edit(b)
for q in sorted({str(q) for q, *_ in e.g.e.m.find(1362427)}):
    os.environ['PART'] = q; log = rvtedit.Edit(b).g.e.trace(1362427)[3]
    f = [l[4] for l in log if 'm_shouldLoadSource' in l[1]]; print(q, f); assert f and all(str(v) in ('1', 'True') for v in f), q
print('OK reload restores all copies')
