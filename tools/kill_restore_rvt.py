"""kill_restore_rvt.py [SCENE.rte]: SIGKILL the process at EVERY os.fsync/replace/rename/unlink/link call of save.restore_backup (after one normal in-place save made a backup). Afterwards the target must be byte-identical to the saved state OR to the original, never anything else, and a second restore must still work. Prints one line per kill point + verdict. Private copy only."""
import os, sys, shutil, hashlib, tempfile, subprocess, signal, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CH = r'''
import sys, os, time
here, p, stop, T = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
os.environ.update(SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_SNAPSHOT_CACHE='0', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=T + '/gate.json')
sys.path[:0] = [os.path.expanduser('~/src/savegate'), here]
if os.environ.get('KR_YEAR'):      # research only: year gate widened in this child process (shipped gate unchanged)
    from savegate import adapters; adapters.RVT_WRITABLE = adapters.RVT_WRITABLE + (os.environ['KR_YEAR'],)
from rvtballet import save, edit
ss = save.SaveSessions(); d = ss.doc('m', p)
if stop < 0:
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': int(os.environ.get('KR_EID', 301595)), 'dx': 1.0})])
    save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % int(os.environ.get('KR_EID', 301595))]}); print('SAVED'); sys.exit(0)
n = [0]
def wrap(name):
    f = getattr(os, name)
    def g(*a, **k):
        n[0] += 1; print('CALL', n[0], name, flush=True)
        if n[0] == stop: time.sleep(900)
        return f(*a, **k)
    setattr(os, name, g)
for nm in ('fsync', 'replace', 'rename', 'unlink', 'link'): wrap(nm)
save.restore_backup(ss, 'm', p, 0); print('RESTORED', n[0], flush=True)
'''
def setup():
    T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); open(T + '/gate.json', 'w').write('{"rvt": {"%s": "open"}}' % os.environ.get('KR_YEAR', '2024'))
    p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p)
    subprocess.run([sys.executable, '-c', CH, HERE, p, '-1', T], check=True, capture_output=True, timeout=900)
    return T, p, h0, sha(p)
def child(T, p, stop):
    pr = subprocess.Popen([sys.executable, '-c', CH, HERE, p, str(stop), T], stdout=subprocess.PIPE, text=True)
    calls = 0
    for line in pr.stdout:
        if line.startswith('CALL'): calls = int(line.split()[1])
        if line.startswith('CALL') and int(line.split()[1]) == stop: time.sleep(0.5); pr.send_signal(signal.SIGKILL); break
    pr.wait(); return calls
T, p, h0, hs = setup(); assert hs != h0
n = 1; bad = 0
while True:
    T, p, h0, hs = setup()
    calls = child(T, p, n)
    now = sha(p); st = 'saved' if now == hs else 'original' if now == h0 else 'OTHER'
    # second restore after the kill must be possible and end at the original
    r2 = subprocess.run([sys.executable, '-c', CH, HERE, p, '99999', T], capture_output=True, text=True, timeout=900)
    fin = sha(p); ok = st != 'OTHER' and fin in (h0, hs)
    print('kill@%d calls_seen=%d state=%s after_second_restore=%s %s' % (n, calls, st, 'original' if fin == h0 else 'saved' if fin == hs else 'OTHER', 'OK' if ok else 'BAD'), flush=True)
    bad += not ok
    if calls < n: break
    n += 1
print('DONE kill points', n - 1, 'bad', bad); sys.exit(1 if bad else 0)
