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
import glob as _g
PRISTINE = sorted(_g.glob(os.path.expanduser('~/rvt-research/corpus/2024/*HVAC.rvt')))[0]   # the seed above was made by the pre-registry generator (its material is not in Global/Latest): the generator must refuse it, and a fresh create is tested on the pristine sample
r = subprocess.run([sys.executable, T, SEED, out, '18435', 'Fresh Material'], capture_output=True, text=True); assert r.returncode != 0 and not os.path.exists(out), 'unregistered-material seed must be refused'
r = subprocess.run([sys.executable, T, PRISTINE, out, '18435', 'Fresh Material'], capture_output=True, text=True); assert r.returncode == 0 and os.path.exists(out), r.stderr
# Revit registers a new material in Global/Latest (u32 count + ascending 8-byte ids): count+1 and the new id appended (paired Revit experiment c5xmat)
sys.path[:0] = [os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')]
import cfb, rvtw, struct
def _latest(f):
    P = rvtw.Stream(cfb.CFB(open(f, 'rb').read()).streams()['Global/Latest'].data).payload; return rvtw.read_member(P, P.find(rvtw.GZ))[0]
_a, _b = _latest(PRISTINE), _latest(out)
assert len(_b) == len(_a) + 8, (len(_a), len(_b))
_i = [i for i in range(len(_b) - 12) if _b[i + 4:i + 12] == struct.pack('<Q', 18435) and _b[i + 12:i + 20] == struct.pack('<Q', 18436)]
assert len(_i) == 1, _i
_n = struct.unpack_from('<I', _b, _i[0])[0]; _ids = [struct.unpack_from('<Q', _b, _i[0] + 4 + 8 * j)[0] for j in range(_n)]
assert _ids == sorted(_ids) and len(set(_ids)) == _n and _b[_i[0] + 4 + 8 * _n:_i[0] + 12 + 8 * _n] == b'\xff' * 8, 'registry malformed'
assert _n == struct.unpack_from('<I', _a, _i[0])[0] + 1 and _ids[-1] > _ids[-2], (_n, _ids[-3:])
import glob
for y in ('2025', '2022'):   # unverified years must be refused with nothing written (2025 used to be written without any check)
    fs = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/%s/*.rvt' % y)))
    if fs:
        if os.path.exists(out): os.remove(out)
        sys.path[:0] = [os.path.expanduser('~/rvt-research'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
        import rvt_geometry as _G
        mats = [e for e, c in _G.file_geometry_index(fs[0]).items() if str(c) == 'MaterialElem']; assert mats, y
        r = subprocess.run([sys.executable, T, fs[0], out, str(mats[0]), 'ZZ'], capture_output=True, text=True); assert r.returncode != 0 and not os.path.exists(out), (y, r.stdout, r.stderr)
print('ok: 7 refusals wrote nothing, unregistered seed refused, fresh name accepted with Latest registry updated')
