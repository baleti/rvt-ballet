"""material-create generator refuses duplicate/invalid names and non-materials, writes nothing (Autodesk HVAC 2024 sample derived file; skips if absent)."""
import os, subprocess, sys, tempfile
SEED = os.path.expanduser('~/c3x-rvttype/mat/m.rvt')   # HVAC 2024 sample + material 1542917 'C3XMAT' (clone of 18435 'Default')
if not os.path.exists(SEED): print('skip: seed absent'); sys.exit(0)
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_mat_create_gen.py')
d = tempfile.mkdtemp(); out = d + '/o.rvt'
def run(eid, name):
    r = subprocess.run([sys.executable, T, SEED, out, str(eid), name], capture_output=True, text=True); return r.returncode, os.path.exists(out)
for eid, name in ((18435, 'c3xmat'), (18435, 'Default'), (18435, 'a:b'), (18435, ' '), (1379030, 'Fresh')):
    rc, ex = run(eid, name); assert rc != 0 and not ex, (eid, name, rc, ex)
rc, ex = run(18435, 'Fresh Material'); assert rc == 0 and ex
print('ok: 5 refusals wrote nothing, fresh name accepted')
