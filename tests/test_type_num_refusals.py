"""c5x-rvttype: set_type_num must refuse (not corrupt) on bad targets: unknown parameter, a String parameter, an instance id, a missing id, NaN/inf. Autodesk 2024 HVAC sample."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read()
cases = [('unknown param', 1379030, 'No Such Param', 1.0), ('string param', 1379030, 'OmniClass Title', 1.0), ('instance id', 1379181, 'Slot Width', 1.0), ('missing id', 999999999, 'Slot Width', 1.0),
         ('nan', 1379030, 'Slot Width', float('nan')), ('inf', 1379030, 'Slot Width', float('inf'))]
bad = 0
for label, eid, nm, v in cases:
    try:
        op = edit.validate_op({'op': 'set_type_num', 'eid': eid, 'param': nm, 'value': v}); out = edit.apply_full(buf, [op])[0]
        save._readback(buf, out, [op]); print('FAIL accepted:', label); bad += 1
    except Exception as x: print('refused', label, type(x).__name__)
sys.exit(1 if bad else 0)
