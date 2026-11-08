"""Hostile move values: nan, inf, -0.0, huge, bool, string are refused by validate_op; two moves of one element compose; moves that cancel vanish; a composed sum beyond the 50000 ft limit is not silently accepted by compose."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.edit import validate_op, compose, EditError
inf = float('inf')
for bad in (float('nan'), inf, -inf, 1e300, 50001.0, True, '1', None, -0.0, 0, 0.0):
    try: validate_op({'op': 'move', 'eid': 5, 'dx': bad, 'dy': 0.0, 'dz': 0.0}); raise SystemExit('FAIL accepted %r' % (bad,))
    except EditError: pass
a = validate_op({'op': 'move', 'eid': 5, 'dx': 1.0}); b = validate_op({'op': 'move', 'eid': 5, 'dx': 2.5, 'dz': -1})
c = compose([a, b]); assert len(c) == 1 and c[0]['dx'] == 3.5 and c[0]['dz'] == -1, c
assert compose([a, validate_op({'op': 'move', 'eid': 5, 'dx': -1.0})]) == []
big = [validate_op({'op': 'move', 'eid': 5, 'dx': 4e4}), validate_op({'op': 'move', 'eid': 5, 'dx': 4e4})]
try: compose(big); raise SystemExit('FAIL composed 8e4 accepted')
except EditError: c = []
assert not c or abs(c[0]['dx']) <= 5e4, 'composed move beyond limit'
print('OK')
