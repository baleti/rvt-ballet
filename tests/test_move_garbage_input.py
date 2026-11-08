"""move/rotate on bytes that are not a usable .rvt must raise (EditError or other clean exception), never return output."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit
F = os.path.expanduser('~/c3x-rvtmatrix-work/keep/2024_finished_spec_example_Ceiling.rte')
cases = {'empty': b'', 'zeros': bytes(4096), 'text': b'hello world' * 100}
if os.path.exists(F):
    b = open(F, 'rb').read(); cases['truncated_half'] = b[:len(b) // 2]; cases['head_only'] = b[:512]
bad = 0
for n, buf in cases.items():
    for o in ({'op': 'move', 'eid': 301782, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}, {'op': 'rotate', 'eid': 301782, 'deg': 30.0}):
        try: out = edit.apply_full(buf, [edit.validate_op(o)]); print('FAIL returned output', n, o['op']); bad += 1
        except Exception as e: print('raised', n, o['op'], type(e).__name__)
sys.exit(1 if bad else 0)
