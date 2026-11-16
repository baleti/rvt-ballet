"""c3x-rvtlink: a ':' that is not the drive designator in a link path is refused (no file needed: guard runs before any write)."""
import os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
from rvtballet import edit
buf = open(SEED, 'rb').read()
for v in ('x:y.rvt', 'a\\b:c.rvt', 'C:\\a:b.rvt', 'C:x.rvt'):
    try: edit.apply(buf, [{'op': 'set_link_path', 'eid': 1363937, 'value': v}])
    except edit.EditError as e: assert "':'" in str(e), (v, str(e)); continue
    raise SystemExit('ACCEPTED %r' % v)
print('OK colon variants refused')
