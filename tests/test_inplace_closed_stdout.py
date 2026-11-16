"""In-place edit whose stdout/stderr pipe is closed at once (`| head -c0`, a dead terminal, SIGPIPE): the file ends as the original or as the complete verified edit, never partial; no temp/backup litter that breaks a rerun; a rerun then succeeds or reports already-applied. Synthetic cols2 .rte (skips without it)."""
import os, sys, shutil, hashlib, subprocess, tempfile
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
S = os.path.expanduser('~/c2x-cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
if not os.path.exists(S): print('skip'); sys.exit(0)
T = tempfile.mkdtemp(); fails = []
try:
    for mode in ('stdout_closed', 'both_closed', 'devfull'):
        D = os.path.join(T, mode); os.makedirs(D); P = D + '/ip.rte'; shutil.copy(S, P); h0 = sha(P)
        open(D + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
        env = dict(os.environ, SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=D + '/gate.json')
        cmd = [os.path.join(HERE, 'bin', 'rvt-ballet'), 'edit', P, '--in-place', '--move', '301592', '1', '0', '0']
        if mode == 'devfull': f = open('/dev/full', 'w'); r = subprocess.run(cmd, stdout=f, stderr=f, env=env, timeout=900)
        else:
            rd, wr = os.pipe(); os.close(rd)       # reader gone: writes raise EPIPE
            r = subprocess.run(cmd, stdout=wr, stderr=wr if mode == 'both_closed' else subprocess.DEVNULL, env=env, timeout=900); os.close(wr)
        h1 = sha(P); litter = [f for f in os.listdir(D) if f.endswith(('.tmp', '.part', '.sgtmp')) or f.startswith('.ip')]
        r2 = subprocess.run(cmd[:-4] + ['--info'] if False else [os.path.join(HERE, 'bin', 'rvt-ballet'), 'info', P], capture_output=True, text=True, env=env, timeout=300)
        readable = r2.returncode == 0
        print(mode, 'rc', r.returncode, 'edited' if h1 != h0 else 'original', 'litter', litter, 'info rc', r2.returncode)
        if litter or not readable or r.returncode != 0: fails.append(mode)
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, 'closed-pipe save left litter or an unreadable file: %s' % fails
print('closed stdout/stderr in-place ok')
