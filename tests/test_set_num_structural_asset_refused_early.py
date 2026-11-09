"""set_num on structural-asset parameters (reader shows placeholder/derived values) must be refused at edit time with a clear message; ordinary numeric params still validate."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path[:0] = [os.path.expanduser('~/src/rvt-viewer'), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
from rvtballet import edit
for nm in ('Unit weight', 'Young modulus X', 'Shear modulus Y', 'Poisson ratio Z', 'Thermal expansion coefficient X'):
    try: edit.validate_op({"op": "set_num", "eid": 1246, "param": nm, "value": 1.0}); raise SystemExit('FAIL: %s accepted' % nm)
    except edit.EditError as ex: assert 'nothing was changed' in str(ex) and 'structural-asset' in str(ex), str(ex)
r = edit.validate_op({"op": "set_num", "eid": 1246, "param": "Cost", "value": 1.0}); assert r['param'] == 'Cost'
print('structural-asset set_num refused early, Cost still accepted OK')
