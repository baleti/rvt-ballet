"""c1x-rvttype: set_type_num to the value the parameter already has must not change any byte outside the (identical) value, or must refuse; set A then back to the original must restore the original bytes of the element stream content (re-edit round trip). Autodesk 2024 HVAC, symbol 1379030 'Slot Width' (1/12 ft)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read()
def ap(b, v):
    op = edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': v}); return edit.apply_full(b, [op])[0]
ORIG = 1 / 12.0
a = ap(buf, ORIG)
print('same value: bytes equal original' if a == buf else 'same value: bytes differ (%d)' % len(a))
b = ap(buf, 0.25); save._readback(buf, b, [edit.validate_op({'op': 'set_type_num', 'eid': 1379030, 'param': 'Slot Width', 'value': 0.25})])
c = ap(b, ORIG)
import rvt_params, tempfile
sys.path[:0] = [os.path.expanduser('~/rvt-research')]
def prm(x):
    p = os.path.join(tempfile.mkdtemp(), 'x.rvt'); open(p, 'wb').write(x); r = rvt_params.params(p); return {k: (v.get('params', v) if isinstance(v, dict) else v) for k, v in r.items()}
p0, p2 = prm(buf), prm(c)
diff = [(k, {n: (p0[k].get(n), p2.get(k, {}).get(n)) for n in set(p0[k]) | set(p2.get(k, {})) if p0[k].get(n) != p2.get(k, {}).get(n)}) for k in p0 if p0[k] != p2.get(k)] + [(k, 'new') for k in p2 if k not in p0]
print('differing elements:', len(diff), diff[:5])
assert p0 == p2, 'edit and edit back changed reader-visible parameters'
print('ok: edit and edit back leaves every reader parameter identical; bytes equal original: %s' % (c == buf))
