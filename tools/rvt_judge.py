#!/usr/bin/env python3
"""rvt_judge.py YEAR ORIG.rvt OUT.rvt EXPECT.json ALLOWED_IDS [WORKDIR]   (c6x-rvtmatrix) one command for the Revit-VM judgement of an edited output:
  1. opens the UNEDITED original (control) and the OUTPUT in the offline Revit VM: both must open with cmp 0/0 and no repair dialog (a DocWarn about the sample itself is shown, not failed),
  2. API readback of every expectation in EXPECT.json (tools/rvt_expect_check.py: values, shifts, rotations, absence),
  3. Revit-side hash of EVERY element and type of ORIGINAL and OUTPUT (tools/rvt_elemhash_*): only ALLOWED_IDS (comma list, the edited elements) may differ; every other differing id is printed and makes the verdict FAIL until explained by a parameter dump (EH_IDS=... tools/rvt_elemhash_readback.py).
Prints one verdict line: JUDGE PASS or JUDGE FAIL <why>. Exit 0 only on PASS. Needs the VM lock (waits); retries 'no Revit port'. Autodesk samples / synthetic only."""
import sys, os, subprocess, re, time
year, orig, out, expf, allowed = sys.argv[1:6]; wd = sys.argv[6] if len(sys.argv) > 6 else os.path.expanduser('~/c6x-rm/judge'); os.makedirs(wd, exist_ok=True)
H = os.path.dirname(os.path.abspath(__file__)); tries = int(os.environ.get('JUDGE_TRIES', '6'))
def run(cmd, tag):
    for k in range(tries):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(H)); o = r.stdout + r.stderr
        if 'no Revit port' in o: time.sleep(120); continue
        open(os.path.join(wd, tag + '.log'), 'w').write(o); return r.returncode, o
    return 3, 'no Revit port after %d tries' % tries
def opened(o): return bool(re.search(r'revit_open=True\tcmp=\(\'0\', \'0\'\)', o)) and 'CorruptModel' not in o and 'Dialog_Revit_Repair' not in o
rc, o1 = run([sys.executable, os.path.join(H, 'rvt_vm_open.py'), year, orig, out], 'open')
rows = [l for l in o1.splitlines() if 'revit_open=' in l]
if len(rows) < 2 or not all(opened(l.replace('revit_open=True', 'revit_open=True', 1)) or ('revit_open=True' in l and "cmp=('0', '0')" in l) for l in rows): print('JUDGE FAIL open/control', rows); sys.exit(1)
rc, o2 = run([sys.executable, os.path.join(H, 'rvt_expect_check.py'), year, orig, out, expf], 'expect')
if rc != 0 or 'fail\': 0' not in o2: print('JUDGE FAIL readback', o2.strip().splitlines()[-3:]); sys.exit(1)
rc, o3 = run([sys.executable, os.path.join(H, 'rvt_elemhash_readback.py'), year, os.path.join(wd, 'eh'), orig, out], 'hash')
if not (os.path.exists(os.path.join(wd, 'eh', '0.txt')) and os.path.exists(os.path.join(wd, 'eh', '1.txt'))): print('JUDGE FAIL oracle: hash step produced no output (not a verdict on the file)', [l for l in o3.splitlines() if 'RESULT' in l][:2]); sys.exit(2)
r = subprocess.run([sys.executable, os.path.join(H, 'rvt_elemhash_compare.py'), os.path.join(wd, 'eh', '0.txt'), os.path.join(wd, 'eh', '1.txt'), allowed], capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode != 0: print('JUDGE FAIL untouched elements: differing ids outside the allowed list (explain by dump before trusting the edit)'); sys.exit(1)
print('JUDGE PASS (control and output open clean, readback exact, only the allowed ids differ in Revit)')
