"""regression: a wall MOVE whose output carries a different displacement (or none) must be refused by save._readback; the honest move passes. The wall's placement origin (Trf.m_or) is the witness (the geometry reader has no mesh for a moved wall)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); E = 301553
mk = lambda dx, dy, dz: edit.validate_op({'op': 'move', 'eid': E, 'dx': dx, 'dy': dy, 'dz': dz})
a, b = mk(1.0, 2.0, 0.5), mk(2.0, 2.0, 0.5)
na = edit.apply_full(buf, [a])[0]
try: save._readback(buf, na, [a])
except sg.VerifyFailed as x: print('FAIL honest wall move refused:', str(x)[:150]); sys.exit(1)
for label, out, ops in (('wrong amount', na, [b]), ('unmoved output', buf, [a])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:100])
print('save readback wall move OK')
