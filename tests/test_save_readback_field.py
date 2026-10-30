"""save._readback for field (name) edits: element must still be present with unchanged parameters; damaged output refused. Pure unit test (reader stubbed)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
op = [{'op': 'set_string', 'eid': 7, 'field': 'Level.m_name', 'value': 'L2'}]
tab = {b'src': {7: {'params': {'a': 1, 'b': 'x'}}}, b'ok': {7: {'params': {'a': 1, 'b': 'x'}}}, b'lost': {}, b'chg': {7: {'params': {'a': 1, 'b': 'y'}}}}
save._read_params = lambda buf: tab[bytes(buf)]
save._readback(b'src', b'ok', op); print('ok output accepted')
for n in (b'lost', b'chg'):
    try: save._readback(b'src', n, op); print('FAIL accepted', n); sys.exit(1)
    except Exception as e: print('refused', n, type(e).__name__)
print('OK')
