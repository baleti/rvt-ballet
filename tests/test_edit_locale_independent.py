"""The edit result does not depend on the process locale: a CJK Mark set under LC_ALL=C, ISO-8859-1 and UTF-8 (PYTHONUTF8 unset) gives byte-identical outputs that read back as the CJK text, and a non-ASCII path under LC_ALL=C is written and the input stays unchanged. Local write-lab scene (skips without it)."""
import os, sys, shutil, hashlib, subprocess, tempfile
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); RB = os.path.join(HERE, 'bin', 'rvt-ballet')
S = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def run(args, loc):
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONUTF8', 'PYTHONIOENCODING', 'LC_ALL', 'LANG', 'LC_CTYPE')}; env.update(LC_ALL=loc, LANG=loc)
    return subprocess.run([RB] + args, capture_output=True, env=env, timeout=600)
def mark(p):
    o = subprocess.run([RB, 'query', 'collect', p, '--class', 'FamilyInstance', '--fields', 'Mark', '--tsv'], capture_output=True, timeout=600).stdout.decode('utf-8', 'replace')
    return [l.split('\t')[-1] for l in o.splitlines() if l.startswith('301610\t')]
T = tempfile.mkdtemp(); fails = []
try:
    shas = {}
    for loc in ('C', 'en_US.ISO-8859-1', 'en_US.UTF-8'):
        out = os.path.join(T, loc + '.rte'); r = run(['edit', S, '--set-string', '301610', 'Mark', '日本語', '-o', out], loc)
        if r.returncode != 0 or not os.path.exists(out): fails.append((loc, 'rc', r.returncode)); continue
        shas[loc] = sha(out)
        if mark(out) != ['日本語']: fails.append((loc, 'mark', mark(out)))
    if len(set(shas.values())) > 1: fails.append(('outputs differ', shas))
    d = os.path.join(T, 'Pläne 日本'); os.makedirs(d); P = d + '/Büro.rte'; shutil.copy(S, P); h0 = sha(P)
    r = run(['edit', P, '--set-string', '301610', 'Mark', 'ä日', '-o', d + '/Büro_out.rte'], 'C')
    if r.returncode != 0 or sha(P) != h0 or mark(d + '/Büro_out.rte') != ['ä日']: fails.append(('path', r.returncode))
    print('outputs', shas, 'fails', fails)
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, fails
print('edit result independent of locale ok')
