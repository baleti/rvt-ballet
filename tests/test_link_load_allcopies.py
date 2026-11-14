"""c3x-rvtlink: set_link_load (unload) on a multi-partition link type edits EVERY copy. Local 2026 Electrical sample (skipped if absent)."""
import os, sys, tempfile
SEED = os.path.expanduser('~/c5x-link/y2526b/e26_seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import rvtedit
from rvtballet import edit
out = os.path.join(tempfile.mkdtemp(), 'o.rvt')
edit._apply_rvtedit(SEED, out, [{'op': 'set_link_load', 'eid': 1362427, 'value': 0}])
e = rvtedit.Edit(out); ps = sorted({str(q) for q, *_ in e.g.e.m.find(1362427)}); print('partitions:', ps); assert len(ps) > 1
for q in ps:
    os.environ['PART'] = q; ee = rvtedit.Edit(out)
    log = ee.g.e.trace(1362427)[3]; f = [l for l in log if 'm_shouldLoadSource' in l[1]]
    print(q, [l[4] for l in f][:1]); assert f and all(str(l[4]) in ('0','False') for l in f), q
print('OK all copies unloaded')
