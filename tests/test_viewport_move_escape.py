"""c4x-rvtmatrix ESCAPE hunt for the opt-in Viewport move: bytes where the viewport really moved by a DIFFERENT amount (dx 7 vs declared 1) or on the other axis (dy 1) must be caught by the product readback (save._readback), the correctly declared one must pass. Autodesk Snowdon Structural 2024 sample (skip if absent). Fails if the Viewport witness in save.py is removed (the move would then be unchecked or refused for another reason: control case below)."""
import os, sys, tempfile
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_VIEWPORTMOVE='1')
import atexit, shutil; atexit.register(shutil.rmtree, _T, True)
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')] + [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/src/savegate')]
from rvtballet import save, edit
S = os.path.expanduser('~/c3x-tmp-c4x/vpout/src.rvt'); E = 779995
if not os.path.exists(S): print('skip'); sys.exit(0)
buf = open(S, 'rb').read()
mv = lambda **k: edit.validate_op(dict({'op': 'move', 'eid': E}, **k))
declared = edit.compose([mv(dx=1.0)])
res = {}
for name, op, ok in (('declared_dx1', mv(dx=1.0), True), ('actual_dx7', mv(dx=7.0), False), ('actual_dy1', mv(dy=1.0), False)):
    nb, _ = edit.apply_full(buf, [op])
    try: save._readback(buf, nb, declared); acc = True; res[name] = 'accepted'
    except BaseException as x: acc = False; res[name] = 'caught:' + type(x).__name__
    assert acc == ok, ('ESCAPE' if acc else 'good output refused', name, res)
print(res); print('OK')
