"""c5x-rvtmatrix RVT-EDIT rung 4: change_type op (FamilyInstance -> another FamilySymbol of the SAME family) on the Autodesk 2024 Snowdon HVAC sample.
Checks: applied (same size, reader Type Id = new type, exactly one element's reader params differ), and refusals (other family, not an instance, same type, op disabled by default). Skipped if the sample is absent."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mk0 = _tf.mkdtemp
def _mk(*a, **k):
    d = _mk0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mk; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
F = [os.path.join(os.path.expanduser('~/rvt-research/corpus/2024'), n) for n in os.listdir(os.path.expanduser('~/rvt-research/corpus/2024')) if n.endswith('HVAC.rvt')]
if not F: print('skip: sample absent'); sys.exit(0)
F = F[0]
import rvt_params
from rvtballet import edit
INST, T_OLD, T_SIB, T_OTHER = 1379181, 1379030, 1530089, 1365172      # instance, its type, a sibling type of the same family, a type of another family
buf = open(F, 'rb').read()
try: edit.validate_op({'op': 'change_type', 'eid': INST, 'type_eid': T_SIB}); raise SystemExit('FAIL: change_type accepted without the opt-in switch')
except edit.EditError as e: print('refused (default off):', str(e)[:60])
os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
op = edit.validate_op({'op': 'change_type', 'eid': INST, 'type_eid': T_SIB})
out, _ = edit.apply_full(buf, [op])
assert len(out) == len(buf) and out != buf, 'size/bytes'
def params(b):
    d = tempfile.mkdtemp(); p = os.path.join(d, 'x.rvt'); open(p, 'wb').write(b); return rvt_params.params(p)
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
p0, p1 = params(buf), params(out)
assert g(p0[INST]).get('Type Id') == str(T_OLD) or g(p0[INST]).get('Type Id') == T_OLD, g(p0[INST]).get('Type Id')
assert str(g(p1[INST]).get('Type Id')) == str(T_SIB), g(p1[INST]).get('Type Id')
diff = [e for e in p0 if e in p1 and g(p0[e]) != g(p1[e])]
assert diff == [INST], diff
print('applied: Type Id %s -> %s, only element %d differs' % (T_OLD, T_SIB, INST))
for label, o in (('other family', {'op': 'change_type', 'eid': INST, 'type_eid': T_OTHER}), ('not an instance', {'op': 'change_type', 'eid': T_OLD, 'type_eid': T_SIB}), ('same type', {'op': 'change_type', 'eid': INST, 'type_eid': T_OLD}), ('target not a type', {'op': 'change_type', 'eid': INST, 'type_eid': INST})):
    try: edit.apply_full(buf, [edit.validate_op(o)]); raise SystemExit('FAIL: accepted ' + label)
    except edit.EditError as e: print('refused', label + ':', str(e)[:80])
for label, t in (('nonexistent type id', 99999999), ('zero', 0)):
    try: edit.apply_full(buf, [edit.validate_op({'op': 'change_type', 'eid': INST, 'type_eid': t})]); raise SystemExit('FAIL: accepted ' + label)
    except edit.EditError as e: print('refused', label + ':', str(e)[:80])
print('OK')
