"""regression (c1x-rvttype): after duplicating a type, a Slot Width edit on the NEW type changes only the new type; the source type keeps its value. Autodesk HVAC 2024 sample; slow; skips if absent. Offline only (not Revit-verified)."""
import glob, os, subprocess, sys, tempfile
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*HVAC.rvt')))
if not F: print('skip: sample absent'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'
sys.path[:0] = [H, os.path.expanduser('~/rvt-research')]
d = tempfile.mkdtemp(); SRC = 1379030
r = subprocess.run([sys.executable, os.path.join(H, 'tools', 'rvt_dup_type_gen.py'), F[0], d + '/a.rvt', str(SRC), 'ISOTEST'], capture_output=True, text=True); assert r.returncode == 0, r.stderr
new = int(r.stdout.split('new ')[1].split()[0])
from rvtballet import edit
out = edit.apply_full(open(d + '/a.rvt', 'rb').read(), [edit.validate_op({'op': 'set_type_num', 'eid': new, 'param': 'Slot Width', 'value': 0.25})])
open(d + '/c.rvt', 'wb').write(out[0] if isinstance(out[0], (bytes, bytearray)) else out[1])
import rvt_params
p = rvt_params.params(d + '/c.rvt'); g = lambda e: (p[e].get('params', p[e]))['Slot Width|Double']
assert abs(g(new) - 0.25) < 1e-12 and abs(g(SRC) - 1 / 12) < 1e-12, (g(new), g(SRC))
print('ok: edit on duplicated type isolated from source type')
