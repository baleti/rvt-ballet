"""SIGINT / SIGHUP / SIGQUIT / SIGTERM sent at several moments to an in-place RVT save: afterwards the file is the original or the complete verified edit (identical to an uninterrupted run), never partial; a signal may leave a .sgtmp / lock file beside the original, but a rerun then sweeps them and saves exactly the uninterrupted result with nothing left. Synthetic cols2 .rte; scratch under ~/c3x-tmp-c4x (skips without the sample)."""
import os, sys, shutil, hashlib, subprocess, signal, time, tempfile
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); RB = os.path.join(HERE, 'bin', 'rvt-ballet')
S = os.path.expanduser('~/c2x-cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
base = os.path.expanduser('~/c3x-tmp-c4x'); os.makedirs(base, exist_ok=True); T = tempfile.mkdtemp(dir=base)
def run(tag, sig=None, delay=0.0):
    D = os.path.join(T, tag); os.makedirs(D); P = D + '/ip.rte'; shutil.copy(S, P); open(D + '/g.json', 'w').write('{"rvt": {"2024": "open"}}')
    env = dict(os.environ, SAVEGATE_GATE=D + '/g.json', SAVEGATE_JOURNAL=D + '/j', SAVEGATE_CACHE=D + '/c', RVTBALLET_ALLOW_OVERWRITE='1')
    p = subprocess.Popen([RB, 'edit', P, '--in-place', '--move', '301592', '1', '0', '0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, start_new_session=True, preexec_fn=lambda: [signal.signal(x, signal.SIG_DFL) for x in (signal.SIGHUP, signal.SIGINT)])      # nohup / '&' make a child ignore HUP / INT: restore the defaults so the signal really lands
    if sig:
        time.sleep(delay)
        try: os.killpg(p.pid, sig)
        except ProcessLookupError: pass
    p.wait(timeout=600); return D, P, env
try:
    D0, P0, _ = run('ref'); good = sha(P0); orig = sha(S); fails = []
    for name, sig in tuple((n, g) for n, g in (('INT', signal.SIGINT), ('HUP', signal.SIGHUP), ('QUIT', signal.SIGQUIT), ('TERM', signal.SIGTERM)) if n in os.environ.get('SIGS', 'INT,HUP,QUIT,TERM').split(',')):
        for delay in (1.0, 8.0, 20.0, 32.0):
            tag = '%s_%g' % (name, delay); D, P, env = run(tag, sig, delay); h = sha(P)
            state = 'original' if h == orig else 'complete' if h == good else 'OTHER'
            litter = [f for f in os.listdir(D) if f not in ('ip.rte', '.savegate', 'g.json', 'j', 'c')]
            print(tag, state, 'litter', litter)
            if state == 'OTHER': fails.append((tag, state)); continue
            if litter and not all(f.endswith(('.sgtmp', '.savegate-lock')) for f in litter): fails.append((tag, 'unexpected litter', litter)); continue
            if state == 'original':      # rerun on the interrupted file: sweeps leftovers, saves the same bytes as an uninterrupted run
                r = subprocess.run([RB, 'edit', P, '--in-place', '--move', '301592', '1', '0', '0'], capture_output=True, text=True, env=env, timeout=900)
                left = [f for f in os.listdir(D) if f not in ('ip.rte', '.savegate', 'g.json', 'j', 'c')]
                print('   rerun rc', r.returncode, 'equals reference', sha(P) == good, 'left', left)
                if r.returncode != 0 or sha(P) != good or left: fails.append((tag, 'rerun', r.returncode, left))
    assert not fails, fails
    print('rvt signal saves ok: original or complete edit in every case')
finally: shutil.rmtree(T, ignore_errors=True)
