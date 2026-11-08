"""c1x-rvttype: two type-level ops in ONE save must either both apply (readback ok, untouched elements unchanged) or refuse; never a half-applied file. change_type(1379181 -> sibling 1530089) + set_type_num(1379030 'Slot Width') on the Autodesk 2024 HVAC sample."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'; os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read()
ops = [edit.validate_op({'op': 'change_type', 'eid': 1379181, 'type_eid': 1530089}), edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 0.25})]
try:
    out = edit.apply_full(buf, ops)[0]
except edit.EditError as x:
    print('refused cleanly:', str(x)[:100]); sys.exit(0)
assert out != buf
save._readback(buf, out, ops)      # raises if either change is missing or anything else differs
print('ok: both ops applied in one save, readback matches')
