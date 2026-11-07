"""regression: two instances moved in one save (+1 and +2 ft): honest claim accepted; swapped amounts are refused (_readback layer; undeclared extra changes are refused by savegate _verify). cols2 synthetic scene (local)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); A, B = 301592, 301595; bad = 0
mk = lambda e, d: edit.validate_op(dict(op='move', eid=e, dx=d, dy=0.0, dz=0.0))
a1, b2, a2, b1 = mk(A, 1.0), mk(B, 2.0), mk(A, 2.0), mk(B, 1.0)
try: nb = edit.apply_full(buf, [a1, b2])[0]
except edit.EditError as x: print('two moves refused at edit:', str(x)[:90]); sys.exit(0)
for lab, ops, want in (('honest', [a1, b2], True), ('swapped amounts', [a2, b1], False)):      # undeclared changes (a claim for only A or only B while both moved) are caught one layer up by savegate core._verify ('changed' outside the manifest), not by _readback
    try: save._readback(buf, nb, ops); got = True
    except sg.VerifyFailed: got = False
    print(lab, 'accepted' if got else 'refused', '' if got == want else 'FAIL'); bad += got != want
sys.exit(1 if bad else 0)
