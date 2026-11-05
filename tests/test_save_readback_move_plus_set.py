"""save._readback: string edit + move on the SAME element in one save. The edited parameter must not trip the move's 'parameters changed' check (it is verified by the set-op check); an unrelated parameter change is still refused. Reader stubbed."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
ops = [{'op': 'set_string', 'eid': 7, 'param': 'Mark', 'value': 'X1'}, {'op': 'move', 'eid': 7, 'dx': 2.0, 'dy': 0.0, 'dz': 0.0}]
tab = {b'src': {7: {'params': {'Mark': 'A', 'a': 1}}}, b'ok': {7: {'params': {'Mark': 'X1', 'a': 1}}},
       b'other': {7: {'params': {'Mark': 'X1', 'a': 2}}}, b'wrongval': {7: {'params': {'Mark': 'Z', 'a': 1}}}}
save._read_params = lambda buf: tab[bytes(buf)]
save._bbox_class = lambda buf, eid: 'FamilyInstance'
save._bbox_of = lambda buf, eid: [[2.0 if bytes(buf) != b'src' else 0.0, 0, 0], [3.0 if bytes(buf) != b'src' else 1.0, 1, 1]]
save._readback(b'src', b'ok', ops); print('set+move accepted')
for n in (b'other', b'wrongval'):
    try: save._readback(b'src', n, ops); print('FAIL accepted', n); sys.exit(1)
    except Exception as e: print('refused', n, type(e).__name__)
print('OK')
