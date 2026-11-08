"""Item 194: rvt_add_clone onto an existing output that is (a) a symlink to a file, (b) a read-only file. Allowed: success with a valid new file at the output (symlink kept or replaced, target never half-written) or a clean refusal with the previous bytes intact. Forbidden: a partial/damaged file at the output or at the symlink target, leftover non-hidden temp files."""
import os, sys, subprocess, tempfile, hashlib
C = os.path.expanduser('~/rvt-research/corpus'); F = C + '/2020/18_rst_basic_sample_project.rvt'
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
if not os.path.exists(F): print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
OLD = b'previous good output'
def run(out): return subprocess.run([sys.executable, TOOL, F, out, '--src', '512451'], capture_output=True, text=True)
with tempfile.TemporaryDirectory() as d:
    tgt = d + '/target.rvt'; open(tgt, 'wb').write(OLD); lnk = d + '/o.rvt'; os.symlink(tgt, lnk)
    r = run(lnk); data = open(lnk, 'rb').read()
    assert r.returncode == 0 and os.path.islink(lnk) and os.path.getsize(tgt) > 1000000 and open(tgt, 'rb').read() == data, 'ADD must write through a symlink output (link kept, target updated)'
    print('symlink: rc', r.returncode, 'link kept', os.path.islink(lnk), 'target size', os.path.getsize(tgt), 'out size', len(data))
    if r.returncode == 0: assert len(data) > 1000000 and data[:8] == bytes.fromhex('d0cf11e0a1b11ae1'), 'success but output not a CFB file'
    else: assert open(tgt, 'rb').read() == OLD, 'refused but target changed'
    assert not [n for n in os.listdir(d) if not n.startswith('.') and n not in ('target.rvt', 'o.rvt')], os.listdir(d)
with tempfile.TemporaryDirectory() as d:
    out = d + '/o.rvt'; open(out, 'wb').write(OLD); os.chmod(out, 0o444)
    r = run(out); data = open(out, 'rb').read()
    print('read-only: rc', r.returncode, 'size', len(data), 'mode', oct(os.stat(out).st_mode & 0o777))
    assert r.returncode != 0 and 'read-only' in r.stdout + r.stderr, 'a read-only output must be refused'
    assert data == OLD and os.stat(out).st_mode & 0o777 == 0o444, 'read-only output changed'
    assert not [n for n in os.listdir(d) if not n.startswith('.') and n != 'o.rvt'], os.listdir(d)
print('OK')
