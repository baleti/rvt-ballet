"""c1x-rvttype: a first string value on a symbol with no AString set needs a NEW object (pair4 diff); it must be refused, never written. Also bad ids. Autodesk 2024 HVAC sample."""
import os, sys, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read(); h = hashlib.sha256(buf).hexdigest()
cases = [('absent set symbol', 1379030, 'Comments', 'x'), ('missing id', 999999999, 'Comments', 'x'), ('unknown param', 1379030, 'No Such Param', 'x')]
bad = 0
for label, eid, nm, v in cases:
    try:
        op = edit.validate_op({'op': 'set_string', 'eid': eid, 'param': nm, 'value': v}); out = edit.apply_full(buf, [op])[0]
        save._readback(buf, out, [op]); print('FAIL accepted:', label); bad += 1
    except Exception as x: print('refused', label, type(x).__name__, str(x)[:80])
if hashlib.sha256(buf).hexdigest() != h: bad += 1
sys.exit(1 if bad else 0)
