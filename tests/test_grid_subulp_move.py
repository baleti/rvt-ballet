"""regression: a Grid move so small that the stored double does not change (dy 1e-17) used to pass validation and the 1e-6 ft gate tolerance while the file stayed byte-identical; now refused at validate_op (< 1e-9 ft), a 1e-3 ft move still works. Autodesk Snowdon HVAC 2024 local copy, opt-in flag on; skipped when absent. NOT Revit-verified."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LEVELMOVE'] = '1'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/42_Snowdon_Towers_Sample_HVAC_FamilyInstance.rvt'); E = 1363058
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read()
for dy in (1e-17, 1e-12, 5e-10):
    try: edit.validate_op({'op': 'move', 'eid': E, 'dx': 0.0, 'dy': dy, 'dz': 0.0}); print('FAIL sub-resolution move accepted', dy); sys.exit(1)
    except edit.EditError as x: print('refused', dy, ':', str(x)[:70])
op = edit.validate_op({'op': 'move', 'eid': E, 'dx': 0.0, 'dy': 1e-3, 'dz': 0.0}); out = edit.apply_full(buf, [op])[0]
if out == buf: print('FAIL 1e-3 ft move left the file unchanged'); sys.exit(1)
save._readback(buf, out, [op]); print('OK')
