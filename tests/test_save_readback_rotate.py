"""regression: a rotate edit whose output is turned by the wrong angle, or only translated, must be refused by save._readback; the honest rotation passes."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit, save
if not os.path.exists(F) or not save._import(): print('skip'); sys.exit(0)
sg = save._import(); buf = open(F, 'rb').read(); E = 301592
mk = lambda op, **k: edit.validate_op(dict(op=op, eid=E, **k))
r90, r30, mv = mk('rotate', deg=90), mk('rotate', deg=30), mk('move', dx=1.0, dy=0.0, dz=0.0)
n90 = edit.apply_full(buf, [r90])[0]; n30 = edit.apply_full(buf, [r30])[0]; nmv = edit.apply_full(buf, [mv])[0]
save._readback(buf, n90, [r90]); save._readback(buf, n30, [r30])      # honest rotations pass
for label, out, ops in (('wrong angle', n30, [r90]), ('translation instead of rotation', nmv, [r90]), ('unrotated output', buf, [r90])):
    try: save._readback(buf, out, ops); print('FAIL accepted:', label); sys.exit(1)
    except sg.VerifyFailed as x: print('refused', label + ':', str(x)[:90])
print('save readback rotate OK')

# a rotate on a wall is refused at edit time with a message that names the supported class
try: edit.apply_full(buf, [edit.validate_op({'op': 'rotate', 'eid': 301553, 'deg': 30})]); print('FAIL wall rotate accepted'); sys.exit(1)
except edit.EditError as x:
    assert 'placed family instances' in str(x), str(x); print('wall rotate refused with a clear message')
