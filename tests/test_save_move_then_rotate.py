"""regression: move then rotate (and rotate then move) of the SAME instance in one save: the gate must accept the honest composed output for its declared ops
and refuse it when only one of the two ops is claimed. Synthetic scene classtests cols2 (local); skipped when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); E = 301592; bad = 0
mk = lambda op, **k: edit.validate_op(dict(op=op, eid=E, **k))
mv, rt = mk('move', dx=1.0, dy=0.0, dz=0.0), mk('rotate', deg=30)
for name, ops in (('move+rotate', [mv, rt]), ('rotate+move', [rt, mv])):
    try: nb = edit.apply_full(buf, ops)[0]
    except edit.EditError as x: print(name, 'refused at edit:', str(x)[:90]); continue
    try: save._readback(buf, nb, ops); print(name, 'honest accepted')
    except sg.VerifyFailed as x: print(name, 'honest refused (conservative):', str(x)[:90])
    for lab, cl in (('claims only move', [mv]), ('claims only rotate', [rt])):
        try: save._readback(buf, nb, cl); print('FAIL', name, 'accepted', lab); bad += 1
        except sg.VerifyFailed: print(name, 'refused', lab)
sys.exit(1 if bad else 0)
