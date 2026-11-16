"""in-place edit while another process holds the file (open for read / flock LOCK_EX / open for write): result must be either refused with the file byte-identical, or saved with backup == original and a complete file (check passes). python tests/test_inplace_held.py"""
import os, sys, shutil, hashlib, subprocess, tempfile, fcntl
S = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S): print('sample absent: skipped'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BIN = os.path.join(HERE, 'bin', 'rvt-ballet')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
T = tempfile.mkdtemp(); fails = []
try:
    for how in ('read', 'flock_ex', 'flock_sh', 'write'):
        D = T + '/' + how; os.makedirs(D); P = D + '/ip.rvt'; shutil.copy(S, P); before = sha(P)
        open(D + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
        env = dict(os.environ, SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=D + '/gate.json')
        fh = open(P, 'r+b' if how == 'write' else 'rb')
        if how == 'flock_ex': fcntl.flock(fh, fcntl.LOCK_EX)
        if how == 'flock_sh': fcntl.flock(fh, fcntl.LOCK_SH)
        r = subprocess.run([BIN, 'edit', P, '--in-place', '--set-string', '1365188', 'Mark', 'heldtest'], capture_output=True, text=True, env=env, timeout=900)
        held_ok = True
        if how in ('read', 'flock_ex', 'flock_sh'):
            fh.seek(0); held_ok = hashlib.sha256(fh.read()).hexdigest() == before   # holder keeps seeing a consistent file
        fh.close()
        saved = sha(P) != before
        bk = [os.path.join(dp, f) for dp, _, fs in os.walk(D) for f in fs if '.savegate' in dp and f.endswith(('.rvt', '.bak')) or ('.savegate' in dp and os.path.getsize(os.path.join(dp, f)) > 1e6)]
        okb = (not saved) or any(sha(b) == before for b in bk)
        chk = subprocess.run([BIN, 'check', P], capture_output=True, text=True).returncode == 0
        ok = held_ok and okb and chk and ((r.returncode == 0 and saved) or (r.returncode != 0 and not saved))
        print(how, 'rc', r.returncode, 'saved', saved, 'holder-consistent', held_ok, 'backup==orig', okb, 'check-clean', chk, 'OK' if ok else 'FAIL', (r.stdout + r.stderr).strip()[-120:] if r.returncode else '')
        if not ok: fails.append(how)
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, fails
print('held-file cases ok')
