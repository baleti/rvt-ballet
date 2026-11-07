"""duplicate-type generator refuses duplicate/invalid names and non-types, writes nothing (Autodesk HVAC sample derived file; skips if absent)."""
import os, subprocess, sys, tempfile
SEED = os.path.expanduser('~/c5x-rm/dup/dup_out.rvt')   # HVAC 2024 sample with type 1542917 'C5XDUP' already added
if not os.path.exists(SEED): print('skip: seed absent'); sys.exit(0)
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_dup_type_gen.py')
d = tempfile.mkdtemp(); out = d + '/o.rvt'
def run(eid, name):
    r = subprocess.run([sys.executable, T, SEED, out, str(eid), name], capture_output=True, text=True); return r.returncode, os.path.exists(out)
for eid, name in ((1379030, 'c5xdup'), (1379030, 'a:b'), (1379030, ' '), (1542918, 'Fresh')):
    rc, ex = run(eid, name); assert rc != 0 and not ex, (eid, name, rc, ex)
rc, ex = run(1379030, 'Fresh Type'); assert rc == 0 and ex
print('ok: 4 refusals wrote nothing, fresh name accepted')
