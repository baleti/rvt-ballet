"""regression (c5x-rvttype): tools/rvt_dup_type_gen.py name handling on the Autodesk 2024 HVAC sample: empty, 300-char, and '<' '>' names are refused (rc != 0, no output); a non-ASCII name is accepted; a second duplicate with an already used name in the same family is refused with nothing written. Skipped if the sample is absent."""
import os, sys, subprocess, tempfile
here = os.path.dirname(os.path.abspath(__file__)); gen = os.path.join(here, '..', 'tools', 'rvt_dup_type_gen.py')
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
if not F: print('skip'); sys.exit(0)
S = F[0]; W = tempfile.mkdtemp(); bad = 0
def run(src, out, name):
    return subprocess.run([sys.executable, gen, src, out, '1379030', name], capture_output=True, text=True, timeout=1800).returncode
for lab, name, ok in (('empty', '', False), ('300 chars', 'x' * 300, False), ('angle', 'a"<b>', False), ('non-ascii', 'Ünï-ß', True)):
    o = os.path.join(W, 'o.rvt')
    rc = run(S, o, name); got = rc == 0 and os.path.exists(o)
    if got != ok or (not ok and os.path.exists(o)): print('FAIL', lab, rc); bad += 1
    else: print('ok', lab)
    if os.path.exists(o): os.remove(o)
a = os.path.join(W, 'a.rvt'); b = os.path.join(W, 'b.rvt')
if run(S, a, 'ZZDUP') != 0: print('FAIL first dup'); bad += 1
elif run(a, b, 'ZZDUP') == 0 or os.path.exists(b): print('FAIL name collision accepted'); bad += 1
else: print('ok collision refused')
sys.exit(1 if bad else 0)
