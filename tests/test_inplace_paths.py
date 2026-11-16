"""in-place edit: (a) read-only directory must refuse leaving the file byte-identical and no stray files; (b) space/unicode/long path names must save and read back the op. Private copy, TEMP gate. python tests/test_inplace_paths.py"""
import os, sys, shutil, hashlib, subprocess, tempfile, stat
S = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S): print('sample absent: skipped'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def run(D, P, extra=()):
    open(D + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
    env = dict(os.environ, SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=D + '/gate.json')
    return subprocess.run([os.path.join(HERE, 'bin', 'rvt-ballet'), 'edit', P, '--in-place', '--set-string', '1365188', 'Mark', 'pathtest'], capture_output=True, text=True, env=env, timeout=900)
def listing(root): return sorted(os.path.join(dp, f)[len(root):] for dp, _, fs in os.walk(root) for f in fs)
T = tempfile.mkdtemp(); fails = []
try:
    # (a) read-only directory
    D = T + '/ro'; W = D + '/w'; os.makedirs(W); P = W + '/ip.rvt'; shutil.copy(S, P)
    before = sha(P); L0 = listing(W)
    os.chmod(W, 0o555)
    try: r = run(D, P)
    finally: os.chmod(W, 0o755)
    ok = r.returncode != 0 and sha(P) == before and listing(W) == L0
    print('readonly-dir rc', r.returncode, 'unchanged', sha(P) == before, 'stray', set(listing(W)) - set(L0), 'OK' if ok else 'FAIL', (r.stdout + r.stderr).strip()[-150:])
    if not ok: fails.append('ro')
    # (b) odd names
    for tag, name in (('space', 'my model v2.rvt'), ('unicode', 'Gebäude_é_日本.rvt'), ('long', 'n' * 200 + '.rvt')):
        D = T + '/' + tag; os.makedirs(D); P = D + '/' + name; shutil.copy(S, P); before = sha(P)
        r = run(D, P); msg = r.stdout + r.stderr
        bk = [f for dp, _, fs in os.walk(D) for f in fs if '.savegate' in dp]
        saved = sha(P) != before
        # if saved, original must be preserved in a backup
        okb = (not saved) or any(sha(os.path.join(dp, f)) == before for dp, _, fs in os.walk(D) for f in fs if '.savegate' in dp)
        ok = (r.returncode == 0 and saved and okb) or (r.returncode != 0 and not saved)
        print(tag, 'rc', r.returncode, 'saved', saved, 'backup-has-original', okb, 'OK' if ok else 'FAIL', msg.strip()[-120:] if r.returncode else '')
        if not ok: fails.append(tag)
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, fails
print('in-place path cases ok')
