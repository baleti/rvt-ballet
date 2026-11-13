"""regression (c5x-rvtmatrix, RVT-EDIT rung 4): a change_type output that carries a different type (or none) must be refused by save._readback; the honest type change passes. Autodesk 2024 HVAC sample; skipped if absent."""
import os, sys
os.environ['RVTBALLET_TEST_ALLOW_DERIVED_TYPE'] = '1'      # these tests exercise save/readback machinery with derived sibling 1530089; Revit itself rejects that swap (see test_changetype_derived_symbol.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F[0], 'rb').read(); INST, T_OLD, T_SIB, T_SIB2 = 1379181, 1379030, 1530089, 1530090
mk = lambda t: edit.validate_op({'op': 'change_type', 'eid': INST, 'type_eid': t})
a = mk(T_SIB); na = edit.apply_full(buf, [a])[0]
try: save._readback(buf, na, [a])
except sg.VerifyFailed as x: print('FAIL honest type change refused:', str(x)[:150]); sys.exit(1)
for label, out, ops in (('wrong type claimed', na, [mk(T_SIB2)]), ('unchanged output', buf, [a])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:110])
print('save readback change_type OK')
