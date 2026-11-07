"""FamilyInstance whose placement origin Trf.m_or is exactly (0,0,0) (host-relative): a move must be refused at edit time, not accepted as a silent no-op.
Needs the Autodesk 2020 HYPERLOOP_MASTER sample (local, large): path in RVT_HYPERLOOP_2020, else skipped."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
p = os.environ.get('RVT_HYPERLOOP_2020', os.path.expanduser('~/rvt-samples/2020_1_HYPERLOOP_MASTER.rvt'))
if not os.path.exists(p): print('SKIP: sample not present'); sys.exit(0)
from rvtballet import edit
b = open(p, 'rb').read()
mv = lambda e: [{'op': 'move', 'eid': e, 'dx': 1.0, 'dy': 0.5, 'dz': 0.0}]
try: edit.apply_full(b, mv(373953)); raise SystemExit('FAIL: zero-origin move accepted')
except edit.EditError as e: assert 'Trf.m_or' in str(e), e
edit.apply_full(b, mv(422779))
print('zero-origin move refused, normal instance move accepted: OK')
