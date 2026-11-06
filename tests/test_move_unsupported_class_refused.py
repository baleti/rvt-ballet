"""regression: moving a Level / Grid (no validated move implementation) is refused cleanly with EditError and nothing written; the TextNote annotation fallback must not leak other classes through.
Autodesk Snowdon HVAC 2024 sample (local copy); skipped when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/42_Snowdon_Towers_Sample_HVAC_FamilyInstance.rvt')
from rvtballet import edit
if not os.path.exists(F): print('skip'); sys.exit(0)
buf = open(F, 'rb').read()
for name, eid, dz in (('Level', 9946, 1.0), ('Grid', 1363057, 0.0)):
    op = edit.validate_op({'op': 'move', 'eid': eid, 'dx': 1.0 if dz == 0 else 0.0, 'dy': 0.0, 'dz': dz})
    try: edit.apply_full(buf, [op]); print('FAIL accepted', name); sys.exit(1)
    except edit.EditError as e: print('refused', name, str(e)[:100])
print('unsupported class moves refused OK')
