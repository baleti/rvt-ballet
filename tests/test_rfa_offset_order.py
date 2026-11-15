"""rfa_set_extrusion_end/start: degenerate values are refused with rc 2 and no output (skipped when synthetic fe2_a / fe6_start_a are absent).
end <= start, start >= end, denormal scale, non-numeric argument; a valid edit still succeeds."""
import os, sys, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__)); TD = os.path.join(H, '..', 'tools'); FL = os.path.expanduser('~/c5x-link/fl/')
def run(tool, src, dst, eid, v): return subprocess.run([sys.executable, os.path.join(TD, tool), src, dst, eid, v], capture_output=True, text=True, timeout=300)
def main():
    T = tempfile.mkdtemp(); n = 0
    if os.path.exists(FL + 'fe2_a.rfa'):
        for v in ('1.7', '1.6999999999999997', '-5', '0.4', '0.39', '1e-320', 'abc', 'nan'):
            o = T + '/e.rfa'; r = run('rfa_set_extrusion_end.py', FL + 'fe2_a.rfa', o, '2916', v)
            assert r.returncode == 2 and not os.path.exists(o), (v, r.returncode, r.stdout); n += 1
        r = run('rfa_set_extrusion_end.py', FL + 'fe2_a.rfa', T + '/ok.rfa', '2916', '3.3'); assert r.returncode == 0, r.stdout; n += 1
    if os.path.exists(FL + 'fe6_start_a.rfa'):
        for v in ('0.4', '1.7', '2.5', '1e-320', 'abc'):
            o = T + '/s.rfa'; r = run('rfa_set_extrusion_start.py', FL + 'fe6_start_a.rfa', o, '2916', v)
            assert r.returncode == 2 and not os.path.exists(o), (v, r.returncode, r.stdout); n += 1
        if os.path.exists(FL + 'fe6_void_a.rfa'):   # void start edit has no Revit-made pair: refused
            o = T + '/v.rfa'; r = run('rfa_set_extrusion_start.py', FL + 'fe6_void_a.rfa', o, '2916', '0.9'); assert r.returncode == 2 and not os.path.exists(o), r.stdout; n += 1
        r = run('rfa_set_extrusion_start.py', FL + 'fe6_start_a.rfa', T + '/oks.rfa', '2916', '0.9'); assert r.returncode == 0, r.stdout; n += 1
    if os.path.exists(FL + 'fe6_start_a.rfa'):   # start then end == end then start (byte-identical)
        A = FL + 'fe6_start_a.rfa'
        for t, sc, x, y in (('rfa_set_extrusion_start.py', 'rfa_set_extrusion_end.py', '0.9', '3.3'), ('rfa_set_extrusion_end.py', 'rfa_set_extrusion_start.py', '3.3', '0.9')):
            assert run(t, A, T + '/c1_' + x + '.rfa', '2916', x).returncode == 0
            assert run(sc, T + '/c1_' + x + '.rfa', T + '/c2_' + x + '.rfa', '2916', y).returncode == 0
        assert open(T + '/c2_0.9.rfa', 'rb').read() == open(T + '/c2_3.3.rfa', 'rb').read(); n += 1
    print('PASS offset order guards: %d cases' % n if n else 'SKIP no synthetic rfa')
main()
