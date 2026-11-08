"""c1x-rvttype: set_type_num is verified on Revit 2024/2026 only; a 2022 sample (symbol 984452 'Depth') used to be built and pass readback unchecked. Must refuse; 2024 still works."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
from rvtballet import edit, save
d22 = os.path.expanduser('~/rvt-research/corpus/2022'); d24 = os.path.expanduser('~/rvt-research/corpus/2024')
F22 = [os.path.join(d22, n) for n in sorted(os.listdir(d22)) if n.endswith('.rvt')][:1] if os.path.isdir(d22) else []
F24 = [os.path.join(d24, n) for n in os.listdir(d24) if n.endswith('HVAC.rvt')] if os.path.isdir(d24) else []
if not F22 or not F24 or not save._import(): print('skip'); sys.exit(0)
def run(f, eid, nm):
    buf = open(f, 'rb').read(); op = edit.validate_op({'op': 'set_type_num', 'eid': eid, 'param': nm, 'value': 1.5})
    return edit.apply_full(buf, [op], src=f)[0] if 'src' in edit.apply_full.__code__.co_varnames else edit.apply_full(buf, [op])[0]
try: run(F22[0], 984452, 'Depth'); print('FAIL: 2022 accepted'); sys.exit(1)
except edit.EditError as x:
    assert 'only verified' in str(x), str(x); print('refused 2022:', str(x)[:80])
run(F24[0], 1379030, 'Slot Width'); print('ok: 2022 refused, 2024 accepted')
