"""material-create generator refuses duplicate/invalid names and non-materials, writes nothing (Autodesk HVAC 2024 sample derived file; skips if absent)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mk0 = _tf.mkdtemp
def _mk(*a, **k):
    d = _mk0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mk; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, subprocess, sys, tempfile
SEED = os.path.expanduser('~/c3x-rvttype/mat/m.rvt')   # HVAC 2024 sample + material 1542917 'C3XMAT' (clone of 18435 'Default')
if not os.path.exists(SEED): print('skip: seed absent'); sys.exit(0)
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_mat_create_gen.py')
d = tempfile.mkdtemp(); out = d + '/o.rvt'
def run(eid, name):
    r = subprocess.run([sys.executable, T, SEED, out, str(eid), name], capture_output=True, text=True); return r.returncode, os.path.exists(out)
for eid, name in ((18435, 'c3xmat'), (18435, 'Default'), (18435, 'a:b'), (18435, ' '), (18435, ' lead'), (18435, 'trail '), (1379030, 'Fresh')):
    rc, ex = run(eid, name); assert rc != 0 and not ex, (eid, name, rc, ex)
rc, ex = run(18435, 'Fresh Material'); assert rc == 0 and ex
import glob
for y in ('2025', '2022'):   # unverified years must be refused with nothing written (2025 used to be written without any check)
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%s/*.rvt' % y)))
    if fs:
        if os.path.exists(out): os.remove(out)
        sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
        import rvt_geometry as _G
        mats = [e for e, c in _G.file_geometry_index(fs[0]).items() if str(c) == 'MaterialElem']; assert mats, y
        r = subprocess.run([sys.executable, T, fs[0], out, str(mats[0]), 'ZZ'], capture_output=True, text=True); assert r.returncode != 0 and not os.path.exists(out), (y, r.stdout, r.stderr)
print('ok: 7 refusals wrote nothing, fresh name accepted')
