"""regression (c1x-rvttype): set_type_num refuses malformed value/param/eid types (bool, str, None, list, empty or None param, negative eid); an int value is normalised to float. Autodesk 2024 HVAC sample; skipped if absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); bad = 0
for lab, e, nm, v in (('bool', 1379030, 'Slot Width', True), ('str', 1379030, 'Slot Width', '0.2'), ('None', 1379030, 'Slot Width', None), ('empty name', 1379030, '', 1.0), ('neg eid', -1, 'Slot Width', 1.0), ('name None', 1379030, None, 1.0), ('list', 1379030, 'Slot Width', [1.0])):
    try: edit.validate_op({'op': 'set_type_num', 'eid': e, 'param': nm, 'value': v}); print('FAIL accepted', lab); bad += 1
    except edit.EditError as x: print('refused', lab)
op = edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 1})
if not isinstance(op['value'], float): print('FAIL int not normalised'); bad += 1
sys.exit(1 if bad else 0)
