"""c3x-rvtdiff: NaN/inf/huge numeric values in move, rotate and set_type_num must be refused (EditError), never written into a record (2024 HVAC)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
for k in ('ENABLE_TYPEPARAM', 'ENABLE_DELETE', 'ENABLE_CHANGETYPE'): os.environ['RVTBALLET_' + k] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit
if not F: print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); bad = 0
nan, inf = float('nan'), float('inf')
ops = [{'op': 'move', 'eid': 1379181, 'dx': nan, 'dy': 0, 'dz': 0}, {'op': 'move', 'eid': 1379181, 'dx': inf, 'dy': 0, 'dz': 0},
       {'op': 'move', 'eid': 1379181, 'dx': 1e300, 'dy': 0, 'dz': 0}, {'op': 'rotate', 'eid': 1379181, 'deg': nan}, {'op': 'rotate', 'eid': 1379181, 'deg': -inf},
       {'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': nan}, {'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': inf}]
for op in ops:
    try:
        edit.apply_full(buf, [edit.validate_op(op)]); print('ACCEPTED', op); bad = 1
    except edit.EditError: pass
    except Exception as x: print('WRONG EXC', op, type(x).__name__, x); bad = 1
if bad: raise SystemExit('FAIL')
print('ok: non-finite values refused')
