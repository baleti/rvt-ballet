"""c4x-rvtmatrix item 53 (severity 1 ESCAPE): deleting a title block instance (FamilyInstance whose owner view is a ViewSheet) must be refused by default; a plain model FamilyInstance delete is still accepted (control, so the guard is not a blanket refusal). Samples: Autodesk HVAC 2026 base (title block 1363537) and Snowdon Structural 2024 (model instance 588559); skip if absent. Without the guard the HVAC delete applied and Revit 2026 then lost 9 elements (measured, see c3x-progress.md)."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
for k in ('RVTBALLET_DELETE_ANY',): os.environ.pop(k, None)
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')] + [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab')]
from rvtballet import edit
H = os.path.expanduser('~/rvtsave-work/c51_hvac2026_base.rvt'); S = os.path.expanduser('~/c3x-tmp-c4x/vpout/src.rvt')
dl = lambda e: [edit.validate_op({'op': 'delete', 'eid': e})]
if os.path.exists(H):
    try: edit.apply_full(open(H, 'rb').read(), dl(1363537)); raise AssertionError('title block delete applied (ESCAPE)')
    except edit.EditError as x: assert 'belongs to a view' in str(x), str(x)
else: print('skip hvac')
if os.path.exists(S):
    out, _ = edit.apply_full(open(S, 'rb').read(), dl(588559)); assert out
else: print('skip structural')
print('OK')
