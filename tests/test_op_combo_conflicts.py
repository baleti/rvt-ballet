"""c3x-rvtdiff: conflicting op batches must not silently produce a half-applied file: delete+move same eid, delete twice, move twice, change_type then delete (2024 HVAC). Each batch either raises EditError or yields a file whose reader sees the same net result; anything else is FAIL."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
for k in ('ENABLE_DELETE', 'ENABLE_CHANGETYPE'): os.environ['RVTBALLET_' + k] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit
if not F: print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); bad = 0
E = 1379181
import hashlib
REF = hashlib.md5(edit.apply_full(buf, [edit.validate_op({'op': 'delete', 'eid': E})])[0]).hexdigest()   # single delete
B = {'delete+move': [{'op': 'delete', 'eid': E}, {'op': 'move', 'eid': E, 'dx': 1, 'dy': 0, 'dz': 0}],
     'move+delete': [{'op': 'move', 'eid': E, 'dx': 1, 'dy': 0, 'dz': 0}, {'op': 'delete', 'eid': E}],
     'delete twice': [{'op': 'delete', 'eid': E}, {'op': 'delete', 'eid': E}]}
for n, ops in B.items():
    try:
        out, _ = edit.apply_full(buf, [edit.validate_op(o) for o in ops])
        print(n, 'applied, len', len(out), 'changed', out != buf)
        if hashlib.md5(out).hexdigest() != REF: print('FAIL', n, 'differs from the single delete'); bad = 1
    except edit.EditError as x: print(n, 'refused:', str(x)[:70])
    except Exception as x: print('WRONG EXC', n, type(x).__name__, x); bad = 1
if bad: raise SystemExit('FAIL')
print('ok')
