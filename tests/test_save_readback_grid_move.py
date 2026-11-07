"""regression: Grid move (opt-in RVTBALLET_ENABLE_LEVELMOVE=1) is witnessed by the Plane.m_origin shift; honest passes, wrong amount / unmoved output / in-plane move are refused.
Autodesk Snowdon HVAC 2024 sample (local copy); skipped when absent. NOT Revit-verified."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/42_Snowdon_Towers_Sample_HVAC_FamilyInstance.rvt'); E = 1363058      # grid 'E', a horizontal grid at y = 41.46 (normal = y)
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read()
mk = lambda dx, dy, dz=0.0: edit.validate_op({'op': 'move', 'eid': E, 'dx': dx, 'dy': dy, 'dz': dz})
os.environ['RVTBALLET_ENABLE_LEVELMOVE'] = '1'
a, b = mk(0.0, 1.0), mk(0.0, 3.0)
na = edit.apply_full(buf, [a])[0]
try: save._readback(buf, na, [a])
except sg.VerifyFailed as x: print('FAIL honest grid move refused:', str(x)[:200]); sys.exit(1)
for label, out, ops in (('wrong amount', na, [b]), ('unmoved output', buf, [a])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:100])
try: edit.apply_full(buf, [mk(1.0, 0.0)]); print('FAIL in-plane move accepted'); sys.exit(1)
except edit.EditError as x: print('refused in-plane:', str(x)[:100])
print('grid move readback OK')
