"""In-place save keeps the file mode (640, 600) and works through a DIRECTORY symlink (real dir edited, link kept, backup in the real dir). Synthetic cols2 .rte (skips without it)."""
import os, sys, shutil, hashlib, subprocess, tempfile
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
S = os.path.expanduser('~/c2x-cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
T = tempfile.mkdtemp(); fails = []
def save(path, tag):
    open(T + '/g.json', 'w').write('{"rvt": {"2024": "open"}}')
    env = dict(os.environ, SAVEGATE_GATE=T + '/g.json', SAVEGATE_JOURNAL=T + '/j' + tag, SAVEGATE_CACHE=T + '/c' + tag, RVTBALLET_ALLOW_OVERWRITE='1')
    return subprocess.run([os.path.join(HERE, 'bin', 'rvt-ballet'), 'edit', path, '--in-place', '--move', '301592', '1', '0', '0'], capture_output=True, text=True, env=env, timeout=900)
try:
    h0 = sha(S); outs = set()
    for m in (0o640, 0o600):
        p = '%s/m%o.rte' % (T, m); shutil.copy(S, p); os.chmod(p, m); r = save(p, '%o' % m)
        ok = r.returncode == 0 and (os.stat(p).st_mode & 0o777) == m and sha(p) != h0
        print('mode', oct(m), 'rc', r.returncode, oct(os.stat(p).st_mode & 0o777), 'OK' if ok else 'FAIL')
        if not ok: fails.append(oct(m))
        outs.add(sha(p))
    os.makedirs(T + '/real'); os.symlink('real', T + '/link'); shutil.copy(S, T + '/real/f.rte')
    r = save(T + '/link/f.rte', 'L'); bk = os.listdir(T + '/real/.savegate') if os.path.isdir(T + '/real/.savegate') else []
    ok = r.returncode == 0 and os.path.islink(T + '/link') and sha(T + '/real/f.rte') != h0 and len(bk) == 1 and sorted(os.listdir(T + '/real')) == ['.savegate', 'f.rte']
    print('dirlink rc', r.returncode, 'backups', len(bk), 'OK' if ok else 'FAIL'); outs.add(sha(T + '/real/f.rte'))
    if not ok: fails.append('dirlink')
    if len(outs) != 1: fails.append('outputs differ')
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, fails
print('mode and directory-symlink saves ok')
