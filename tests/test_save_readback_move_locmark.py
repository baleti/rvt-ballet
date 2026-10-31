"""save._readback for a move: the derived column location mark may gain a grid-offset suffix; any other parameter change is still refused. Pure unit test (reader stubbed)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
op = [{'op': 'move', 'eid': 7, 'dx': 2.0}]
M = 'Column Location Mark|String'
tab = {b'src': {7: {'params': {M: 'D-1', 'a': 1}}}, b'ok': {7: {'params': {M: 'D-1(610)', 'a': 1}}},
       b'other': {7: {'params': {M: 'D-1', 'a': 2}}}, b'rewrite': {7: {'params': {M: 'E-2', 'a': 1}}}, b'both': {7: {'params': {M: 'D-1(610)', 'a': 2}}}}
save._read_params = lambda buf: tab[bytes(buf)]
save._readback(b'src', b'ok', op); print('suffix accepted')
for n in (b'other', b'rewrite', b'both'):
    try: save._readback(b'src', n, op); print('FAIL accepted', n); sys.exit(1)
    except Exception as e: print('refused', n, type(e).__name__)
print('OK')
