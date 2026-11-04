"""kill_during_restore.py FILE.rte|rvt [TRIALS=40]: SAVE! once in-place (one move edit of element 301595 of 2024_writer_cols2.rte; other files need EID edit) to create a backup, then RESTORE in a child SIGKILLed a random time (0..1.5 x measured restore time) after the child announced READY.
After every kill the file must be the saved version or the original, byte-identical (never partial), and a following restore must still work. Prints outcome counts. Synthetic/Autodesk-sample files only."""
import os, sys, shutil, tempfile, subprocess, hashlib, time, random, signal
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHILD = r'''
import sys
sys.path.insert(0, sys.argv[1])
from rvtballet import save
ss = save.SaveSessions()
if sys.argv[3] == "save":
    from rvtballet import edit
    d = ss.doc("m1", sys.argv[2]); nb, _ = edit.apply_full(d.buf, [edit.validate_op({"op": "move", "eid": 301595, "dx": 1.0})])
    save.save_overwrite(ss, "m1", sys.argv[2], new_bytes=nb, manifest={"modified": ["el:301595"]}); print("DONE"); sys.exit()
print("READY", flush=True); save.restore_backup(ss, "m1", sys.argv[2], 0); print("DONE")
'''
sha = lambda b: hashlib.sha256(b).hexdigest()
f = sys.argv[1]; trials = int(sys.argv[2]) if len(sys.argv) > 2 else 40; ext = os.path.splitext(f)[1]
w = tempfile.mkdtemp(prefix='kdrs-'); side = tempfile.mkdtemp(prefix='kdrs2-'); open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}')
env = dict(os.environ, SAVEGATE_GATE=side + '/g.json', SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_LAYOUT_CHANGE='1')
p = os.path.join(w, 'a' + ext); shutil.copy(f, p); h0 = sha(open(p, 'rb').read())
run = lambda mode: subprocess.run([sys.executable, '-c', CHILD, HERE, p, mode], env=env, capture_output=True, text=True, timeout=1800)
assert 'DONE' in run('save').stdout; hs = sha(open(p, 'rb').read()); assert hs != h0, 'edit produced identical bytes'
t = time.time(); assert 'DONE' in run('restore').stdout; T = time.time() - t; print('restore child total %.2f s (incl. imports); saved==orig bytes: %s' % (T, hs == h0), flush=True)
tot = {}; bad = 0
for k in range(trials):
    shutil.copy(f, p); assert 'DONE' in run('save').stdout; hs = sha(open(p, 'rb').read())
    pr = subprocess.Popen([sys.executable, '-c', CHILD, HERE, p, 'restore'], env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    pr.stdout.readline(); time.sleep(random.uniform(0, float(os.environ.get('MAXDELAY', '0.05'))))
    if pr.poll() is None: pr.send_signal(signal.SIGKILL)
    pr.wait(); h = sha(open(p, 'rb').read())
    out = 'ORIGINAL' if h == h0 else 'SAVED' if h == hs else 'CORRUPT'
    r = run('restore')
    if 'DONE' not in r.stdout: out += '+STUCK'
    elif sha(open(p, 'rb').read()) not in (h0, hs): out += '+RESTORE_WRONG'      # a later restore(0) restores the NEWEST backup, which after a restore is the pre-restore file: original or saved are both fine, anything else is not
    tot[out] = tot.get(out, 0) + 1; bad += ('CORRUPT' in out or 'STUCK' in out or 'WRONG' in out)
    lo = [x for x in os.listdir(w) if x.endswith(('.sgtmp', '.lock')) or 'tmp' in x or 'lock' in x]
    if lo: tot['leftover'] = tot.get('leftover', 0) + 1; print('leftover:', lo, flush=True)
print(tot, 'BAD' if bad else 'OK'); shutil.rmtree(w, True); shutil.rmtree(side, True); sys.exit(1 if bad else 0)
