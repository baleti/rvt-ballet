"""Top/Base Offset edit: the derived 'Unconnected Height|Double' may move by exactly the offset delta, nothing else (synthetic, no file needed)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.save import _offset_echo
K = 'Unconnected Height|Double'
x = {'Top Offset': 0.0, K: 76.75, 'Base Offset': 0.0}
assert _offset_echo('Top Offset', x, {'Top Offset': 2.0, K: 78.75}) == {K}
assert _offset_echo('Top Offset', x, {'Top Offset': 2.0, K: 79.0}) == set()          # wrong delta stays an undeclared change
assert _offset_echo('Top Offset', x, {'Top Offset': 2.0, K: 74.75}) == set()         # wrong sign for Top
assert _offset_echo('Base Offset', {'Base Offset': 0.0, K: 76.75}, {'Base Offset': 2.0, K: 74.75}) == {K}
assert _offset_echo('Offset', x, {'Offset': 2.0, K: 78.75}) == set()                 # other parameters get no exemption
print('ok')
