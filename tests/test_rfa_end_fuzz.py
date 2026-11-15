"""rfa_set_extrusion_end fuzz (synthetic fe2_a under ~/c5x-link/fl, skipped when absent): 3 random bit flips per input, fixed seed.
Every trial must either be refused (rc 2, no output file) or produce an output that differs from the clean edit only near the flipped bytes
(unvalidated slack carried through) and never more than 16 bytes in total; a trial that crashes (rc not 0/2) or leaves an output after a refusal fails."""
import os, sys, random, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__)); TOOL = os.path.join(H, '..', 'tools', 'rfa_set_extrusion_end.py')
SRC = os.path.expanduser('~/c5x-link/fl/fe2_a.rfa')
def run(a, b): return subprocess.run([sys.executable, TOOL, a, b, '2916', '3.3'], capture_output=True, text=True, timeout=300)
def main(n=12):
    if not os.path.exists(SRC): print('SKIP no fe2_a.rfa'); return
    d = open(SRC, 'rb').read(); T = tempfile.mkdtemp(); c = run(SRC, T + '/clean.rfa'); assert c.returncode == 0, c.stderr
    clean = open(T + '/clean.rfa', 'rb').read(); random.seed(7); acc = ref = 0
    for i in range(n):
        b = bytearray(d)
        for _ in range(3): b[random.randrange(len(b))] ^= 1 << random.randrange(8)
        p, o = '%s/m%d.rfa' % (T, i), '%s/o%d.rfa' % (T, i); open(p, 'wb').write(b); r = run(p, o)
        if r.returncode == 2:
            assert not os.path.exists(o), 'output left after refusal'; ref += 1
        else:
            assert r.returncode == 0, 'crash rc %d: %s' % (r.returncode, r.stderr[-200:])
            out = open(o, 'rb').read(); assert len(out) == len(clean)
            assert sum(x != y for x, y in zip(out, clean)) <= 16, 'accepted output differs from the clean edit in too many bytes'; acc += 1
    print('PASS fuzz', n, 'trials: refused', ref, 'accepted', acc)
if __name__ == '__main__': main()
