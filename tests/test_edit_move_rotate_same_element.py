"""move + rotate of ONE element in one save (the editor refuses a second move/rotate per session): edit._apply_rvtedit runs them as consecutive passes.
The output must equal moving then rotating by two separate apply_full calls, and save._readback must accept it for BOTH ops (net move AND rotation). cols2 scene (write-lab); skip when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'); E = 301595
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
buf = open(F, 'rb').read()
mv = edit.validate_op({'op': 'move', 'eid': E, 'dx': 2.0, 'dy': 0.0, 'dz': 0.0}); ro = edit.validate_op({'op': 'rotate', 'eid': E, 'deg': 30})
both = edit.apply_full(buf, [mv, ro])[0]
seq = edit.apply_full(edit.apply_full(buf, [mv])[0], [ro])[0]
assert both != buf and len(both) > 0
assert both == seq, 'one-save move+rotate differs from two sequential saves'
save._readback(buf, both, [mv, ro]); print('readback accepts net move + rotation')
try: save._readback(buf, edit.apply_full(buf, [mv])[0], [mv, ro]); print('FAIL move-only output accepted for move+rotate'); sys.exit(1)
except Exception as x: print('refused move-only:', type(x).__name__)
print('move+rotate same element OK')
