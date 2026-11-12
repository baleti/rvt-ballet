"""in-place edit of DAMAGED copies of an Autodesk sample is refused and the file is left byte-identical (no backup, nothing written).
Uses ~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt (skipped when absent), a private copy and a TEMP gate file (the real gate is not touched). python tests/test_inplace_damaged.py"""
import os, sys, shutil, hashlib, subprocess, tempfile
S = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S): print('sample absent: skipped'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def damage(p, how):
    n = os.path.getsize(p)
    if how == 'flip_mid':
        with open(p, 'r+b') as f: f.seek(11_000_000); f.write(b'\x5a')
    elif how == 'trunc1':
        with open(p, 'r+b') as f: f.truncate(n - 1)
    elif how == 'zero_block':
        with open(p, 'r+b') as f: f.seek(2000 * 4096); f.write(b'\0' * 16 * 4096)
    elif how == 'trunc100k':
        with open(p, 'r+b') as f: f.truncate(n - 102400)
T = tempfile.mkdtemp(); fails = []
try:
    for how in ('flip_mid', 'trunc1', 'zero_block', 'trunc100k'):
        D = os.path.join(T, how); os.makedirs(D); P = D + '/ip.rvt'; shutil.copy(S, P); damage(P, how); before = sha(P)
        open(D + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
        env = dict(os.environ, SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=D + '/gate.json')
        r = subprocess.run([os.path.join(HERE, 'bin', 'rvt-ballet'), 'edit', P, '--in-place', '--set-string', '1365188', 'Mark', 'x'], capture_output=True, text=True, env=env, timeout=900)
        bk = [f for dp, _, fs in os.walk(D) for f in fs if '.savegate' in dp]
        msg = (r.stdout + r.stderr).lower()
        ok = r.returncode == 3 and sha(P) == before and not bk and ('damaged' in msg or 'cut short' in msg or 'corrupt' in msg)
        print(how, 'rc', r.returncode, 'unchanged', sha(P) == before, 'backups', len(bk), 'OK' if ok else 'FAIL')
        if not ok: fails.append(how)
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, 'damaged source not refused cleanly: %s' % fails
print('in-place damaged-source refusals ok')
