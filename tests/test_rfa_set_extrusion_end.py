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
    b = bytearray(4000); struct.pack_into('<d', b, 72, 1.7); struct.pack_into('<d', b, 120, 1.7)
    for st, nw in ((1.0, 3.3), (0.4, 1.0), (0.4, 0.0)):      # unit/zero values collide with constants
        try: T.patch_body_generic(bytes(b), nw, 0.7 if st == 1.0 else st); raise SystemExit('FAIL colliding value accepted')
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
        # header slot and R-record ParamValueDouble (what the Revit API reads) must carry the new end offset, and no old-valued slot may remain
        so_s = SE.Session(out); i, rr, log, q = so_s.trace(eid)
        pvals = [struct.unpack('<d', so_s.J.get(l[2], 8))[0] for l in log if l[1] == 'ParamValueDouble.m_value' and l[3] - l[2] == 8]
        assert any(abs(v - new) < 1e-12 for v in pvals), 'R record lacks new end offset %r' % pvals
        e0 = struct.unpack_from('<d', zbody(pa)[0], 72)[0]
        pe = struct.pack('<d', e0); assert len(SE.occurrences(so_s.sp, [pe])[pe]) == len(SE.occurrences(SE.Session(pb).sp, [pe])[pe]), 'old end offset slots differ from the Revit-made file'
        hb = SE.Session(pb).template(eid)['hdr']; ho = so_s.template(eid)['hdr']
        assert abs(sum(1 for o in range(len(ho) - 7) if abs(struct.unpack_from('<d', ho, o)[0] - new) < 1e-12) - sum(1 for o in range(len(hb) - 7) if abs(struct.unpack_from('<d', hb, o)[0] - new) < 1e-12)) == 0
        r2 = subprocess.run([sys.executable, TOOL, pa, out, str(eid), str(new)], capture_output=True, text=True); assert r2.returncode == 2 and 'exists' in r2.stdout
        r3 = subprocess.run([sys.executable, TOOL, pa, os.path.join(d, 'x.rfa'), '2917', str(new)], capture_output=True, text=True); assert r3.returncode == 2 and 'not ExtrusionElem' in r3.stdout
        assert not os.path.exists(os.path.join(d, 'x.rfa'))
    print('pair', a, '->', b, 'ok')


synthetic_refusals(); pair('fe_a.rfa', 'fe_b.rfa', 2916, 2.5); pair('fe2_a.rfa', 'fe2_b.rfa', 2916, 3.3); pair('fe6_void_a.rfa', 'fe6_void_b.rfa', 2916, 3.3)
for _n in ('hex', 'circ', 'tri'): pair('fe4_%s_a.rfa' % _n, 'fe4_%s_b.rfa' % _n, 2916, 3.3)
fa = os.path.join(FL, 'fe2_a.rfa')
if os.path.exists(fa):
    with tempfile.TemporaryDirectory() as d:
        for bad in ('1e9', 'nan', 'inf'):
            r = subprocess.run([sys.executable, TOOL, fa, os.path.join(d, 'b.rfa'), '2916', bad], capture_output=True, text=True)
            assert r.returncode == 2 and not os.path.exists(os.path.join(d, 'b.rfa')), 'bad new value %s accepted' % bad
if os.path.exists(fa):
    with tempfile.TemporaryDirectory() as d:
        c1, c2, c3 = (os.path.join(d, n) for n in ('c1.rfa', 'c2.rfa', 'c3.rfa'))
        for a_, b_, v in ((fa, c1, '3.3'), (c1, c2, '2.5'), (fa, c3, '2.5')):
            assert subprocess.run([sys.executable, TOOL, a_, b_, '2916', v], capture_output=True).returncode == 0
        assert open(c2, 'rb').read() == open(c3, 'rb').read(), 'chained edit differs from the direct edit'
smp = '~/rvt-samples/racbasicsamplefamily-2025.rfa'
if os.path.exists(smp):
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, TOOL, smp, os.path.join(d, 'o.rfa'), '82', '7.5'], capture_output=True, text=True)
        assert r.returncode == 2 and not os.path.exists(os.path.join(d, 'o.rfa')) and 'measured on Revit 2024' in r.stdout, 'non-2024 file accepted: ' + r.stdout
with tempfile.TemporaryDirectory() as d:
    z = os.path.join(d, 'z.rfa'); open(z, 'wb').write(bytes(100))
    r = subprocess.run([sys.executable, TOOL, z, os.path.join(d, 'o.rfa'), '2916', '3.3'], capture_output=True, text=True)
    assert r.returncode == 2 and 'refused' in r.stdout and not os.path.exists(os.path.join(d, 'o.rfa')), r.stdout + r.stderr
    if os.path.exists(fa):
        t = os.path.join(d, 't.rfa'); open(t, 'wb').write(open(fa, 'rb').read()[:300000])
        r = subprocess.run([sys.executable, TOOL, t, os.path.join(d, 'o2.rfa'), '2916', '3.3'], capture_output=True, text=True)
        assert r.returncode == 2 and not os.path.exists(os.path.join(d, 'o2.rfa')), 'truncated file accepted'
fc = os.path.join(FL, 'fe5_col_a.rfa')      # profile coordinates 1.7 x 1.3 equal E and E-start on purpose: refused (ambiguous), nothing written
if os.path.exists(fc):
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, TOOL, fc, os.path.join(d, 'o.rfa'), '2916', '3.3'], capture_output=True, text=True)
        assert r.returncode == 2 and not os.path.exists(os.path.join(d, 'o.rfa')), 'collision file accepted: ' + r.stdout
print('PASS')
