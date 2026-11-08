"""regression (c1x-rvttype): tools/rvt_dup_type_gen.py must refuse (rc != 0, no output file, input untouched) on a non-symbol id, missing id, negative id, non-numeric id and output path == input. Autodesk 2024 HVAC sample; skipped if absent."""
import os, sys, subprocess, tempfile, hashlib
here = os.path.dirname(os.path.abspath(__file__)); gen = os.path.join(here, '..', 'tools', 'rvt_dup_type_gen.py')
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
if not F: print('skip'); sys.exit(0)
S = F[0]; h = lambda p: hashlib.sha1(open(p, 'rb').read()).hexdigest(); h0 = h(S); W = tempfile.mkdtemp(); bad = 0
for lab, tid, out in (('instance', '1379181', 'o1'), ('missing', '999999999', 'o2'), ('negative', '-1', 'o3'), ('non-numeric', 'abc', 'o4'), ('out==in', '1379030', None)):
    o = S if out is None else os.path.join(W, out + '.rvt')
    r = subprocess.run([sys.executable, gen, S, o, tid, 'C1XBAD'], capture_output=True, text=True, timeout=1800)
    if r.returncode == 0 or (out and os.path.exists(o)): print('FAIL accepted', lab); bad += 1
    else: print('refused', lab)
if h(S) != h0: print('FAIL input modified'); bad += 1
sys.exit(1 if bad else 0)
