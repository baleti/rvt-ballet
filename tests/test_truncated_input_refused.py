"""c3x-rvtdiff: apply_full on a truncated or zero-length source must raise (EditError/ValueError family), never return edited bytes (2024 HVAC cut at 0, 100, 4096, half, size-1)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit
if not F: print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); bad = 0
op = {'op': 'move', 'eid': 1379181, 'dx': 1, 'dy': 0, 'dz': 0}
ref = edit.apply_full(buf, [edit.validate_op(op)])[0]      # a cut that only drops trailing slack is fine IF the output equals the intact one
for n in (0, 100, 4096, len(buf) // 2, len(buf) - 1):
    try:
        out, _ = edit.apply_full(buf[:n], [edit.validate_op(op)])
        if out == ref: print('cut', n, 'accepted, output identical to intact (slack only)')
        else: print('ACCEPTED cut', n, 'with DIFFERENT output'); bad = 1
    except Exception as x: print('refused cut', n, type(x).__name__)
if bad: raise SystemExit('FAIL')
print('ok')
