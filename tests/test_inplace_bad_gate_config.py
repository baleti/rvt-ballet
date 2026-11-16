"""Fail closed: an in-place edit with a missing, empty, garbage, wrong-type or year-closed gate config never writes: the original keeps its sha, no backup dir is made. Control: a valid 'open' gate saves. Local Autodesk sample (skips without it)."""
import os, sys, shutil, hashlib, subprocess, tempfile
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
S = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
if not os.path.exists(S): print('skip'); sys.exit(0)
CASES = {'garbage': 'not json {{{', 'empty': '', 'list': '[]', 'wrong_type': '{"rvt": "open"}', 'closed': '{"rvt": {"2024": "closed"}}', 'other_year': '{"rvt": {"2025": "open"}}', 'null_year': '{"rvt": {"2024": null}}', 'missing': None, 'control': '{"rvt": {"2024": "open"}}'}
T = tempfile.mkdtemp(); fails = []
try:
    for name, body in CASES.items():
        D = os.path.join(T, name); os.makedirs(D); P = D + '/ip.rvt'; shutil.copy(S, P); before = sha(P)
        G = D + '/gate.json'
        if body is not None: open(G, 'w').write(body)
        env = dict(os.environ, SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=G)
        r = subprocess.run([os.path.join(HERE, 'bin', 'rvt-ballet'), 'edit', P, '--in-place', '--set-string', '1365188', 'Mark', 'x'], capture_output=True, text=True, env=env, timeout=900)
        bk = [f for dp, _, fs in os.walk(D) for f in fs if '.savegate' in dp]
        unchanged = sha(P) == before
        ok = (not unchanged) if name == 'control' else (unchanged and r.returncode != 0 and not bk)
        print(name, 'rc', r.returncode, 'unchanged', unchanged, 'backups', len(bk), 'OK' if ok else 'FAIL', (r.stdout + r.stderr).strip()[-100:].replace('\n', ' '))
        if not ok: fails.append(name)
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, 'gate config not fail-closed: %s' % fails
print('bad gate configs fail closed')
