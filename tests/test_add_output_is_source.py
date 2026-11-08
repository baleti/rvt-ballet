"""Item 196: rvt_add_clone with the output path equal to the source (same file, via plain path, symlink, hardlink). Must either refuse with the source byte-identical, or (only if it succeeds) leave a valid file; never a truncated/partial source."""
import os, sys, subprocess, tempfile, hashlib, shutil
F = os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
if not os.path.exists(F): print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
with tempfile.TemporaryDirectory() as d:
    src = d + '/s.rvt'; shutil.copy(F, src); h = sha(src); os.symlink(src, d + '/l.rvt'); os.link(src, d + '/h.rvt')
    for name in ('s.rvt', 'l.rvt', 'h.rvt'):
        r = subprocess.run([sys.executable, TOOL, src, d + '/' + name, '--src', '512451'], capture_output=True, text=True)
        now = sha(src); print(name, 'rc', r.returncode, 'source unchanged', now == h, ('| ' + (r.stdout + r.stderr).strip()[-120:]) if r.returncode else '')
        if r.returncode: assert now == h, name + ': refused but source changed'
        else: assert os.path.getsize(src) > 1000000 and open(src, 'rb').read(8) == bytes.fromhex('d0cf11e0a1b11ae1'); h = now
        assert not [n for n in os.listdir(d) if not n.startswith('.') and n not in ('s.rvt', 'l.rvt', 'h.rvt')], os.listdir(d)
print('OK')
