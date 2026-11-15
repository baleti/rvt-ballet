"""rfa_set_extrusion_start: Z item, header and R record equal Revit's own result for the Revit-made start-offset pair (synthetic, local ~/c5x-link/fl; skipped when absent); refusals leave no output."""
import os, sys, struct, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..'); sys.path.insert(0, R)
from rvtballet import segedit as SE
FL = os.path.expanduser('~/c5x-link/fl'); TOOL = os.path.join(R, 'tools', 'rfa_set_extrusion_start.py')


def parts(p, eid=2916):
    s = SE.Session(p); t = s.template(eid); W = s.ctx.W; zk = t['_zk']; L = struct.unpack('<I', s.J.get(zk + W + 4, 4))[0]
    i, r, log, q = s.trace(eid)
    return s.J.get(zk + W + 8, L), t['hdr'], [s.J.get(l[2], 8) for l in log if l[1] == 'ParamValueDouble.m_value' and l[3] - l[2] == 8]


def run(a, b, v, eid='2916'): return subprocess.run([sys.executable, TOOL, a, b, eid, v], capture_output=True, text=True)


pa, pb = os.path.join(FL, 'fe6_start_a.rfa'), os.path.join(FL, 'fe6_start_b.rfa')
if os.path.exists(pa) and os.path.exists(pb):
    with tempfile.TemporaryDirectory() as d:
        o = os.path.join(d, 'o.rfa'); r = run(pa, o, '0.9'); assert r.returncode == 0, r.stdout + r.stderr
        assert parts(o) == parts(pb), 'Z/header/R differ from the Revit-made file'
        r = run(pa, o, '0.9'); assert r.returncode == 2 and 'exists' in r.stdout
        for bad in ('nan', '1e9', '1.0', '0'):
            x = os.path.join(d, 'x%s.rfa' % bad); r = run(pa, x, bad); assert r.returncode == 2 and not os.path.exists(x), 'bad value %s accepted' % bad
        x = os.path.join(d, 'y.rfa'); r = run(pa, x, '0.9', '2917'); assert r.returncode == 2 and not os.path.exists(x)
    print('pair ok')
fc = os.path.join(FL, 'fe5_col_a.rfa')
if os.path.exists(fc):
    with tempfile.TemporaryDirectory() as d:
        x = os.path.join(d, 'c.rfa'); r = run(fc, x, '0.9'); assert r.returncode == 2 and not os.path.exists(x), 'collision file accepted: ' + r.stdout
print('PASS')
