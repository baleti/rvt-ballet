"""A reader polling the target during an in-place RVT save only ever sees the original bytes or the complete edit (never a partial/truncated file)."""
import os, sys, shutil, hashlib, subprocess, tempfile, threading
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); RB = os.path.join(HERE, 'bin', 'rvt-ballet')
S = os.path.expanduser('~/c2x-cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
sha = lambda b: hashlib.sha256(b).hexdigest()
base = os.path.expanduser('~/c3x-tmp-c4x'); os.makedirs(base, exist_ok=True); T = tempfile.mkdtemp(dir=base)
try:
    P = T + '/ip.rte'; shutil.copy(S, P); open(T + '/g.json', 'w').write('{"rvt": {"2024": "open"}}')
    env = dict(os.environ, SAVEGATE_GATE=T + '/g.json', SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_ALLOW_OVERWRITE='1')
    orig = sha(open(S, 'rb').read()); seen = {}; stop = threading.Event()
    def poll():
        while not stop.is_set():
            try: h = sha(open(P, 'rb').read())
            except FileNotFoundError: h = 'MISSING'
            seen[h] = seen.get(h, 0) + 1
    t = threading.Thread(target=poll); t.start()
    r = subprocess.run([RB, 'edit', P, '--in-place', '--move', '301592', '1', '0', '0'], capture_output=True, text=True, env=env, timeout=900)
    stop.set(); t.join(); final = sha(open(P, 'rb').read())
    bad = {h: n for h, n in seen.items() if h not in (orig, final)}
    print('rc', r.returncode, 'reads', sum(seen.values()), 'distinct', len(seen), 'bad', bad)
    assert r.returncode == 0 and final != orig and not bad, (r.returncode, bad)
    print('reader saw only original or complete edit')
finally: shutil.rmtree(T, ignore_errors=True)
