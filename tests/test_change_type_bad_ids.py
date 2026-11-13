"""regression (c1x-rvttype): change_type with a nonexistent / zero / negative / out-of-range type id (or instance id) must be refused, never accepted or crash. Autodesk 2024 HVAC sample; skipped if absent."""
import os, sys
os.environ['RVTBALLET_TEST_ALLOW_DERIVED_TYPE'] = '1'      # these tests exercise save/readback machinery with derived sibling 1530089; Revit itself rejects that swap (see test_changetype_derived_symbol.py)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); INST = 1379181
bad = 0
for label, eid, t in (('missing type', INST, 999999999), ('zero', INST, 0), ('negative', INST, -1), ('2**64', INST, 2**64), ('missing inst', 999999999, 1530089), ('neg inst', -5, 1530089)):
    try:
        edit.apply_full(buf, [edit.validate_op({'op': 'change_type', 'eid': eid, 'type_eid': t})]); print('FAIL: accepted', label); bad += 1
    except SystemExit: raise
    except Exception as e: print('refused', label, type(e).__name__, str(e)[:70])
sys.exit(1 if bad else 0)
