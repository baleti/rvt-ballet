"""c1x-rvtlink item 92: trailing separator and doubled separators in a link path are refused (guard runs before any write); UNC prefix and plain drive paths stay accepted by this guard."""
import os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
from rvtballet import edit
buf = open(SEED, 'rb').read()
for v in ('C:\\a\\', 'C:\\a\\\\b.rvt', 'C:\\a//b.rvt'):
    try: edit.apply(buf, [{'op': 'set_link_path', 'eid': 1363937, 'value': v}])
    except edit.EditError as e: assert 'separator' in str(e), (v, str(e)); continue
    raise SystemExit('ACCEPTED %r' % v)
print('OK separator variants refused')
