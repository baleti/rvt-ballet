"""c4x-rvtdiff 157: resave-equivalence criterion. Header-only changes are tolerated only with the flag; a body change, an added or a removed element always fails."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from rvt_resave_equiv import classify
H = {'id': 441, 'header_changed': True, 'rec_len': [[], []], 'fields': []}
B = {'id': 7, 'header_changed': False, 'rec_len': [[], []], 'fields': [['x', 1, 2]]}
L = {'id': 8, 'header_changed': True, 'rec_len': [[1], [2]], 'fields': []}
assert classify({'changed': []}) == (True, [], [])
assert classify({'changed': [H]})[0] is False and classify({'changed': [H]}, True) == (True, [441], [])
assert classify({'changed': [H, B]}, True)[0] is False
assert classify({'changed': [L]}, True)[0] is False          # length change is a body change
assert classify({'changed': [], 'added': [5]}, True)[0] is False and classify({'changed': [], 'removed': [5]}, True)[0] is False
print('OK')
