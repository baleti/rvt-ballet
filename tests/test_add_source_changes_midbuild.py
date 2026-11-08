"""Item 197: the source of rvt_add_clone is overwritten in place (bytes flipped mid-file) after the build has started (hidden .part seen). Allowed: output identical to the baseline built from the pristine source (consistent snapshot), or a refusal. Forbidden: a success whose output differs from the baseline (a mix of old and new source bytes)."""
import os, sys, subprocess, tempfile, hashlib, shutil, time
F = os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
if not os.path.exists(F): print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
with tempfile.TemporaryDirectory() as d:
    src = d + '/s.rvt'; shutil.copy(F, src); base = d + '/base.rvt'
    r = subprocess.run([sys.executable, TOOL, src, base, '--src', '512451'], capture_output=True, text=True); assert r.returncode == 0, r.stdout + r.stderr
    p = subprocess.Popen([sys.executable, TOOL, src, d + '/o.rvt', '--src', '512451'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t = time.time()
    while p.poll() is None and not [n for n in os.listdir(d) if '.part' in n] and time.time() - t < 600: time.sleep(0.005)
    n = os.path.getsize(src)
    with open(src, 'r+b') as f:      # corrupt several places, same size, in place
        for off in (n // 5, n // 2, n * 4 // 5): f.seek(off); b = f.read(64); f.seek(off); f.write(bytes(x ^ 0xFF for x in b))
    out, _ = p.communicate(); o = d + '/o.rvt'
    if p.returncode != 0: print('refused:', out.strip()[-150:]); assert not os.path.exists(o)
    else: print('success; equals baseline:', sha(o) == sha(base)); assert sha(o) == sha(base), 'output mixes old and new source bytes'
print('OK')
