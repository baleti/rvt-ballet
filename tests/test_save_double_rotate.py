"""regression: rotate 30 then rotate 60 of the SAME instance in one save: output must not pass for a single-rotation claim of 30 or 60 alone; 90 total (or the honest pair) is fine. cols2 synthetic scene (local)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); E = 301592; bad = 0
mk = lambda d: edit.validate_op(dict(op='rotate', eid=E, deg=d))
a, b, c = mk(30), mk(60), mk(90)
try: nb = edit.apply_full(buf, [a, b])[0]
except edit.EditError as x: print('double rotate refused at edit:', str(x)[:90]); sys.exit(0)
for lab, ops, want in (('honest pair (conservative: gate checks each op against the source)', [a, b], False), ('total 90 as one op', [c], True), ('claims only 30', [a], False), ('claims only 60', [b], False)):
    try: save._readback(buf, nb, ops); got = True
    except sg.VerifyFailed: got = False
    print(lab, 'accepted' if got else 'refused', '' if got == want else 'FAIL'); bad += got != want
sys.exit(1 if bad else 0)
