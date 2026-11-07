"""regression (c5x-rvttype, RVT-EDIT rung 4): set_type_num readback must find the type parameter under its reader key 'Caption|Double'; before the fix the honest edit was refused ('reads None'). Wrong claimed value and unchanged output must still be refused. Autodesk 2024 HVAC sample (HVAC type 1379030 'Slot Width')."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F[0], 'rb').read()
mk = lambda v: edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': v})
a = mk(0.1); na = edit.apply_full(buf, [a])[0]
try: save._readback(buf, na, [a])
except sg.VerifyFailed as x: print('FAIL honest type param edit refused:', str(x)[:200]); sys.exit(1)
for label, out, ops in (('wrong value claimed', na, [mk(0.2)]), ('unchanged output', buf, [a])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:110])
print('save readback set_type_num OK')
