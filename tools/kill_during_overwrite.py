"""kill_during_overwrite.py FILE.rfa|rvt [TRIALS=30]: in-place SAVE! (rvtballet.save.save_overwrite, no edit, gate opened by a throwaway config) in a child that is SIGKILLed after a random delay (0..1.1 x the measured full time); afterwards the file must be byte-identical to the original or a complete valid file (CFB readable, same stream names); then a clean SAVE! must work again. Exit 1 on CORRUPT or STUCK."""
import os, sys, shutil, tempfile, subprocess, hashlib, time, random, signal
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHILD = r'''
import sys
sys.path.insert(0, sys.argv[1])
from rvtballet import save
ss = save.SaveSessions(); r = save.save_overwrite(ss, "m1", sys.argv[2]); print("SAVED")
'''
def streams(b):
    sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import cfb
    return sorted(e.name for e in cfb.CFB(b).entries if e.type == 2)
f = sys.argv[1]; trials = int(sys.argv[2]) if len(sys.argv) > 2 else 30; ext = os.path.splitext(f)[1]
orig = open(f, 'rb').read(); h0 = hashlib.sha256(orig).hexdigest(); s0 = streams(orig)
w = tempfile.mkdtemp(prefix='kdr-'); side = tempfile.mkdtemp(prefix='kdrs-'); open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}')
env = dict(os.environ, SAVEGATE_GATE=side + '/g.json', SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', RVTBALLET_ALLOW_OVERWRITE='1')
p = os.path.join(w, 'a' + ext); shutil.copy(f, p)
t = time.time(); subprocess.run([sys.executable, '-c', CHILD, HERE, p], env=env, capture_output=True, timeout=1800); T = time.time() - t
print('full save %.1f s' % T, flush=True); tot = {}; bad = 0
for k in range(trials):
    shutil.copy(f, p)
    pr = subprocess.Popen([sys.executable, '-c', CHILD, HERE, p], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: pr.wait(timeout=random.uniform(T * float(os.environ.get("LO", "0")), T * 1.1))
    except subprocess.TimeoutExpired: pr.send_signal(signal.SIGKILL); pr.wait()
    b = open(p, 'rb').read()
    if hashlib.sha256(b).hexdigest() == h0: out = 'ORIGINAL'
    else:
        try: out = 'NEW-VALID' if streams(b) == s0 else 'CORRUPT(streams)'
        except Exception as e: out = 'CORRUPT(%s)' % type(e).__name__
    r = subprocess.run([sys.executable, '-c', CHILD, HERE, p], env=env, capture_output=True, text=True, timeout=1800)
    if 'SAVED' not in r.stdout: out += '+STUCK'
    tot[out] = tot.get(out, 0) + 1; bad += out.startswith('CORRUPT') or 'STUCK' in out
    if [x for x in os.listdir(w) if x.endswith(('.sgtmp', '.lock'))]: tot['leftover'] = tot.get('leftover', 0) + 1
print(tot, 'BAD' if bad else 'OK'); shutil.rmtree(w, True); shutil.rmtree(side, True); sys.exit(1 if bad else 0)
