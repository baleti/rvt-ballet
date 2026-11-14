"""in-place edit of a file that has a hard-link partner: afterwards the partner must be byte-identical to the original (link broken by atomic rename) or to the new file; never a mixed/damaged third state. python tests/test_inplace_hardlink.py"""
import os, sys, shutil, hashlib, subprocess, tempfile
S = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S): print('sample absent: skipped'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
D = tempfile.mkdtemp()
try:
    P = D + '/ip.rvt'; L = D + '/partner.rvt'; shutil.copy(S, P); os.link(P, L); h0 = sha(P)
    open(D + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
    env = dict(os.environ, SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=D + '/gate.json')
    r = subprocess.run([os.path.join(HERE, 'bin', 'rvt-ballet'), 'edit', P, '--in-place', '--set-string', '1365188', 'Mark', 'x'], capture_output=True, text=True, env=env, timeout=1800)
    hp, hl = sha(P), sha(L)
    print('rc', r.returncode, 'dest changed', hp != h0, 'partner==orig', hl == h0, 'partner==dest', hl == hp, (r.stdout + r.stderr)[-200:].replace('\n', ' '))
    assert hl in (h0, hp), 'partner is a third state'
    assert r.returncode == 0 or hp == h0, 'refused but dest changed'
    print('hardlink in-place ok')
finally: shutil.rmtree(D, ignore_errors=True)
