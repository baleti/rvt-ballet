"""Hostile rotate values: nan/inf/bool/str/None/>360/multiples of 360/-0.0 refused; 90+90 composes to 180; 180+180 vanishes; 30 then -30 vanishes."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.edit import validate_op, compose, EditError
for bad in (float('nan'), float('inf'), -float('inf'), True, '90', None, 361, -360.5, 360, -360, 0, -0.0, 1e300, 1e-12, 1e-7, 360 - 1e-8):
    try: validate_op({'op': 'rotate', 'eid': 5, 'deg': bad}); raise SystemExit('FAIL accepted %r' % (bad,))
    except EditError: pass
r = lambda d: validate_op({'op': 'rotate', 'eid': 5, 'deg': d})
c = compose([r(90), r(90)]); assert len(c) == 1 and c[0]['deg'] == 180, c
assert compose([r(180), r(180)]) == [] and compose([r(30), r(-30)]) == []
print('OK')
