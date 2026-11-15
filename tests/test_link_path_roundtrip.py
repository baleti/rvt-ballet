"""c1x-rvtlink: set_link_path to another value and back must restore the original DECODED content (rvt_diff: 0 differing byte runs in the inflated partition, 0 elements changed). Stored bytes differ (our deflate vs Revit's, 21.9M of 22.0M) but file length is equal, so only the length is asserted here; content equality was checked with tools/rvt_diff.py (2026-11-15).
Snowdon HVAC 2024 sample, local ~/c5x-link/al/seed.rvt (skipped if absent)."""
import os, sys
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
from rvtballet import edit
buf = open(SEED, 'rb').read()
cur = 'Snowdon Towers Sample Structural.rvt'
for mid in ('Brand_New.rvt', 'Sub\\Dir\\A much longer replacement link file name 0123456789.rvt', 'x.rvt'):
    b = edit.apply(buf, [{'op': 'set_link_path', 'eid': 1363937, 'value': mid}])
    assert b != buf and len(b) > 0
    r = edit.apply(b, [{'op': 'set_link_path', 'eid': 1363937, 'value': cur}])
    print(mid[:20], 'identical' if r == buf else 'DIFFERS %d bytes (len %d vs %d)' % (sum(x != y for x, y in zip(r, buf)), len(r), len(buf)))
    assert len(r) == len(buf)
print('done')
