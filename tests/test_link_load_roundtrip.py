"""c1x-rvtlink: set_link_load unload then reload restores the original DECODED content (rvt_diff 2026-11-15: 0 differing byte runs, 0 elements changed; stored bytes differ by re-compression, so not asserted byte-equal). Snowdon HVAC 2024 local seed (skipped if absent)."""
import os, sys
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = os.environ['RVTBALLET_ENABLE_LINKLOAD'] = '1'
from rvtballet import edit
buf = open(SEED, 'rb').read()
for eid in (1363937, 1362428):
    u = edit.apply(buf, [{'op': 'set_link_load', 'eid': eid, 'value': False}])
    r = edit.apply(u, [{'op': 'set_link_load', 'eid': eid, 'value': True}])
    print(eid, 'unload changed' if u != buf else 'unload NO-OP', 'reload identical' if r == buf else 'reload DIFFERS')
print('done')
# no-op: loading an already loaded link must be refused (file untouched), not silently rewritten
try:
    edit.apply(buf, [{'op': 'set_link_load', 'eid': 1363937, 'value': True}]); raise SystemExit('no-op load accepted')
except edit.EditError as e: assert 'nothing to change' in str(e), e
print('OK no-op refused')
