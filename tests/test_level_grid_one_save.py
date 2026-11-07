"""regression: Level (+1 ft along its normal) and Grid (+1 ft) moved in ONE save (opt-in flag): honest claim accepted; swapped amounts refused. Autodesk Snowdon HVAC 2024 local copy; skipped when absent. NOT Revit-verified."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LEVELMOVE'] = '1'
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/42_Snowdon_Towers_Sample_HVAC_FamilyInstance.rvt'); L, G = 9946, 1363057
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); bad = 0
mk = lambda e, dx, dz: edit.validate_op({'op': 'move', 'eid': e, 'dx': dx, 'dy': 0.0, 'dz': dz})
l1, g1, l2, g2 = mk(L, 0.0, 1.0), mk(G, 1.0, 0.0), mk(L, 0.0, 2.0), mk(G, 2.0, 0.0)
try: nb = edit.apply_full(buf, [l1, g1])[0]
except edit.EditError as x: print('refused at edit:', str(x)[:100]); sys.exit(0)
for lab, ops, want in (('honest', [l1, g1], True), ('swapped (L2,G2)', [l2, g2], False), ('L claimed 2', [l2, g1], False), ('G claimed 2', [l1, g2], False)):
    try: save._readback(buf, nb, ops); got = True
    except sg.VerifyFailed as x: got = False; why = str(x)[:80]
    print(lab, 'accepted' if got else 'refused', '' if got == want else 'FAIL'); bad += got != want
sys.exit(1 if bad else 0)
