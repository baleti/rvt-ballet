"""regression: a MOVE whose output displacement differs from the declared one (right element, parameters untouched, wrong place) must be refused by save._readback; the honest move passes. 2024 cols2 synthetic scene (write-lab); skip when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read()
mk = lambda dx, dy: edit.validate_op({'op': 'move', 'eid': 301595, 'dx': dx, 'dy': dy, 'dz': 0.0})
nb, _ = edit.apply_full(buf, [mk(1.0, 0.5)])
save._readback(buf, nb, [mk(1.0, 0.5)])                    # honest displacement passes
for label, ops in (('wrong amount', [mk(3.0, 0.5)]), ('wrong axis', [mk(0.5, 1.0)])):
    try: save._readback(buf, nb, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:110])
try: save._readback(buf, buf, [mk(1.0, 0.5)]); print('FAIL unmoved output accepted'); sys.exit(1)
except sg.VerifyFailed as x: print('refused unmoved:', str(x)[:110])
print('save readback move displacement OK')
