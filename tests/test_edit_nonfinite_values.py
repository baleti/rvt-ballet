"""c1x-rvtsave 207: non-finite or absurd numbers in edit ops (nan, inf, 1e308, bool, string) must be refused by validate_op/apply_full, never written into a file. Synthetic 2024 .rte."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read(); n = 0
for bad in (float('nan'), float('inf'), -float('inf'), 1e308, True, '1.0', None, [1.0]):
    for key in ('dx', 'dy', 'dz'):
        try:
            out, _ = edit.apply_full(buf, [edit.validate_op({'op': 'move', 'eid': 301595, key: bad})])
        except Exception as e:
            n += 1; continue
        raise SystemExit('FAIL accepted %s=%r' % (key, bad))
print('OK: %d non-finite/odd move values refused' % n)
