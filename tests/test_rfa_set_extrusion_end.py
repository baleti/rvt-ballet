"""rfa_set_extrusion_end: the patched Z item equals Revit's own result for both Revit-made pairs (synthetic families, local files under ~/c5x-link/fl; skipped when absent),
and the tool refuses a non-extrusion element, an existing output, and a Z body whose slots do not hold the expected values."""
import os, sys, struct, subprocess, tempfile, zlib
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..'); sys.path.insert(0, R)
from rvtballet import segedit as SE
sys.path.insert(0, os.path.join(R, 'tools')); import rfa_set_extrusion_end as T
FL = os.path.expanduser('~/c5x-link/fl')
TOOL = os.path.join(R, 'tools', 'rfa_set_extrusion_end.py')


def zbody(path, eid=2916):
    s = SE.Session(path); t = s.template(eid); W = s.ctx.W; zk = t['_zk']; L = struct.unpack('<I', s.J.get(zk + W + 4, 4))[0]
    return s.J.get(zk + W + 8, L), struct.unpack('<I', s.J.get(zk + W, 4))[0]


def synthetic_refusals():
    try: T.patch_body(bytes(7072), 3.0); raise SystemExit('FAIL non-3060 Z item accepted')
    except SE.Refused: pass
    b = bytearray(3060); struct.pack_into('<d', b, 72, 1.0); struct.pack_into('<d', b, 120, 2.0)
    try: T.patch_body(bytes(b), 3.0); raise SystemExit('FAIL disagreeing slots accepted')
    except SE.Refused: pass
    struct.pack_into('<d', b, 120, 1.0); struct.pack_into('<d', b, 837, 5.0)
    try: T.patch_body(bytes(b), 3.0); raise SystemExit('FAIL body with wrong slot values accepted')
    except SE.Refused: pass
    print('synthetic refusals ok')


def pair(a, b, eid, new):
    pa, pb = os.path.join(FL, a), os.path.join(FL, b)
    if not (os.path.exists(pa) and os.path.exists(pb)): print('skip pair', a); return
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, 'o.rfa'); r = subprocess.run([sys.executable, TOOL, pa, out, str(eid), str(new)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        zo, so = zbody(out); zb, sb = zbody(pb)
        assert zo == zb, 'Z body differs from the Revit-made file'
        assert so == sb == zlib.adler32(zo) & 0xffffffff
        r2 = subprocess.run([sys.executable, TOOL, pa, out, str(eid), str(new)], capture_output=True, text=True); assert r2.returncode == 2 and 'exists' in r2.stdout
        r3 = subprocess.run([sys.executable, TOOL, pa, os.path.join(d, 'x.rfa'), '2917', str(new)], capture_output=True, text=True); assert r3.returncode == 2 and 'not ExtrusionElem' in r3.stdout
        assert not os.path.exists(os.path.join(d, 'x.rfa'))
    print('pair', a, '->', b, 'ok')


synthetic_refusals(); pair('fe_a.rfa', 'fe_b.rfa', 2916, 2.5); pair('fe2_a.rfa', 'fe2_b.rfa', 2916, 3.3)
print('PASS')
