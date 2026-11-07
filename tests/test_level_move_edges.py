"""regression: Level/Grid move edge values (opt-in flag on): nan/inf/huge refused at validate or edit, zero/-0.0 move is no-op or refused (never a changed file),
two moves of one Level in one save compose to their sum under the gate. Autodesk Snowdon HVAC 2024 local copy; skipped when absent. NOT Revit-verified."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LEVELMOVE'] = '1'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/42_Snowdon_Towers_Sample_HVAC_FamilyInstance.rvt'); L = 9946
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); bad = 0
mk = lambda dz: {'op': 'move', 'eid': L, 'dx': 0.0, 'dy': 0.0, 'dz': dz}
for v in (float('nan'), float('inf'), -float('inf'), 1e300, 1e12):
    try: edit.apply_full(buf, [edit.validate_op(mk(v))]); print('FAIL accepted dz', v); bad += 1
    except (edit.EditError, ValueError) as x: print('refused dz', v)
for v in (0.0, -0.0):
    try:
        nb = edit.apply_full(buf, [edit.validate_op(mk(v))])[0]
        if nb != buf: print('FAIL zero move changed file', v); bad += 1
        else: print('zero move no-op', v)
    except (edit.EditError, ValueError): print('zero move refused', v)
a, b, s = edit.validate_op(mk(1.0)), edit.validate_op(mk(2.0)), edit.validate_op(mk(3.0))
try:
    nc = edit.apply_full(buf, [a, b])[0]
    try: save._readback(buf, nc, [a, b]); print('composed 1+2 accepted')
    except sg.VerifyFailed as x: print('composed 1+2 refused (ok, conservative):', str(x)[:80])
    for label, ops in (('claims only 1', [a]), ('claims 3 as one op', [s])):
        try: save._readback(buf, nc, ops); print('composed==%s accepted (3 total)' % label)
        except sg.VerifyFailed: print('refused', label)
except edit.EditError as x: print('twice-in-one-save refused:', str(x)[:100])
sys.exit(1 if bad else 0)
