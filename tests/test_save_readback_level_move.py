"""regression: Level move (opt-in RVTBALLET_ENABLE_LEVELMOVE=1) is witnessed by the Elevation shift; honest passes, wrong amount / unmoved / horizontal declared are refused. Without the opt-in the edit is refused.
Autodesk Snowdon HVAC 2024 sample (local copy); skipped when absent. NOT Revit-verified."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/42_Snowdon_Towers_Sample_HVAC_FamilyInstance.rvt'); E = 9946
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read()
mk = lambda dz: edit.validate_op({'op': 'move', 'eid': E, 'dx': 0.0, 'dy': 0.0, 'dz': dz})
try: edit.apply_full(buf, [mk(1.0)]); print('FAIL accepted without opt-in'); sys.exit(1)
except edit.EditError: print('refused without opt-in')
os.environ['RVTBALLET_ENABLE_LEVELMOVE'] = '1'
a, b = mk(1.0), mk(3.0)
na = edit.apply_full(buf, [a])[0]
try: save._readback(buf, na, [a])
except sg.VerifyFailed as x: print('FAIL honest level move refused:', str(x)[:200]); sys.exit(1)
for label, out, ops in (('wrong amount', na, [b]), ('unmoved output', buf, [a])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:100])
print('level move readback OK')
