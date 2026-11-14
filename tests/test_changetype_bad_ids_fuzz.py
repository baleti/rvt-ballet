"""c3x-rvtdiff: change_type with garbage ids (0, -1, 2**63, 2**64-1, element of non-symbol class, instance as target) must raise EditError, never another exception and never return bytes (2024 HVAC)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit
if not F: print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); bad = 0
for eid, t in [(1379181, 0), (1379181, -1), (1379181, 2**63), (1379181, 2**64-1), (1379181, 1379181), (0, 1379030), (-5, 1379030), (2**64-1, 1379030), (1379181, 1), (1, 1379030)]:
    try:
        edit.apply_full(buf, [edit.validate_op({'op': 'change_type', 'eid': eid, 'type_eid': t})]); print('ACCEPTED', eid, t); bad = 1
    except edit.EditError: pass
    except Exception as x: print('WRONG EXC', eid, t, type(x).__name__, x); bad = 1
if bad: raise SystemExit('FAIL')
print('ok: all garbage ids refused with EditError')
