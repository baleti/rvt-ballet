"""regression: a TextNote MOVE is verified by TextElement.m_orig; honest move passes, wrong amount / unmoved output are refused.
Autodesk Snowdon HVAC 2024 sample (local copy); skipped when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/42_Snowdon_Towers_Sample_HVAC_FamilyInstance.rvt'); E = 1422186
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read()
mk = lambda dx: edit.validate_op({'op': 'move', 'eid': E, 'dx': dx, 'dy': 2.0, 'dz': 0.0})
a, b = mk(1.0), mk(2.0)
na = edit.apply_full(buf, [a])[0]
try: save._readback(buf, na, [a])
except sg.VerifyFailed as x: print('FAIL honest text note move refused:', str(x)[:200]); sys.exit(1)
for label, out, ops in (('wrong amount', na, [b]), ('unmoved output', buf, [a])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:100])
print('textnote move readback OK')
