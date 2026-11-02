"""kill_every_call_rvt.py FILE.rfa : RVT twin of dwg-viewer tools/kill_every_call.py. save_overwrite with a real edit (SymbolInfo.m_name = KillEveryCall); os.fsync/replace/rename/unlink/link wrapped; the child is SIGKILLed at every such call. Afterwards: target byte-identical to the original, or complete with the edit readable (wledit trace) AND a backup byte-equal to the original present; a clean re-save works. A clean re-save must work (SAVED) or be refused cleanly by LayoutChanged with the file untouched. Exit 1 on any violation."""
import os, sys, shutil, tempfile, subprocess, hashlib, signal, glob
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = r'''
import sys, os, time
here, p, stop = sys.argv[1], sys.argv[2], int(sys.argv[3]); sys.path.insert(0, here)
from rvtballet import save
ss = save.SaveSessions(); ss.doc("m1", p)
save.add_edit(ss, "m1", p, {"op": "set_string", "eid": 0, "field": "SymbolInfo.m_name", "value": os.environ.get("EVAL", "KillEveryCall")})
n = [0]
def wrap(name):
    f = getattr(os, name)
    def g(*a, **k):
        n[0] += 1; print("CALL", n[0], name, flush=True)
        if n[0] == stop: time.sleep(900)
        return f(*a, **k)
    setattr(os, name, g)
for nm in ("fsync", "replace", "rename", "unlink", "link"): wrap(nm)
try: save.save_overwrite(ss, "m1", p); print("SAVED", flush=True)
except BaseException as e: print("REFUSED", type(e).__name__, flush=True)
'''
f = sys.argv[1]; src = open(f, 'rb').read(); h0 = hashlib.sha256(src).hexdigest()
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import wledit
def edited(p):
    q = tempfile.mktemp(suffix='.rfa'); shutil.copy(p, q)
    try: return any(l[1] == 'SymbolInfo.m_name' and l[4] == 'KillEveryCall' for l in wledit.Editor(q).trace(0)[3])
    except Exception: return False
    finally: os.remove(q)
side = tempfile.mkdtemp(); open(side + '/c.json', 'w').write('{"allow_overwrite": true}'); open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}')
env = dict(os.environ, PYTHONPATH=os.path.expanduser('~/src/savegate'), SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', DWG_BALLET_CONFIG=side + '/c.json', SAVEGATE_GATE=side + '/g.json', RVTBALLET_ALLOW_OVERWRITE='1')
sha = lambda x: hashlib.sha256(open(x, 'rb').read()).hexdigest()
def run(stop):
    w = tempfile.mkdtemp(); p = w + '/a.rfa'; shutil.copy(f, p)
    pr = subprocess.Popen([sys.executable, '-c', CH, HERE, p, str(stop)], env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True); calls = []
    for line in pr.stdout:
        calls.append(line.split()[1:] if line.startswith('CALL') else line.strip())
        if stop and line.startswith('CALL %d ' % stop): pr.send_signal(signal.SIGKILL); break
    pr.wait(); return w, p, calls
w, p, calls = run(0); shutil.rmtree(w, True); w, p, calls = run(0); names = [c[1] for c in calls if isinstance(c, list)]; total = len(names); print('calls in a warm full save:', total, names[:40]); shutil.rmtree(w, True)
bad = 0; res = {}
for k in range(1, total + 1):
    w, p, calls = run(k); now = sha(p)
    bks = [x for pat in (w + '/.savegate/*', w + '/*.bak*', side + '/c/*/*') for x in glob.glob(pat) if os.path.isfile(x) and not x.endswith('.part')]
    if now == h0: st = 'orig'
    else:
        st = 'new' if edited(p) else 'PARTIAL'
        if st == 'new' and not any(sha(x) == h0 for x in bks): st = 'NEW-WITHOUT-BACKUP'
    ok = st in ('orig', 'new')
    if ok:
        r = subprocess.run([sys.executable, '-c', CH, HERE, p, '0'], env=dict(env, EVAL='KillEveryCall2'), capture_output=True, text=True, timeout=1800); ok = 'SAVED' in r.stdout or ('REFUSED LayoutChanged' in r.stdout and sha(p) == now)      # a 2nd edit of the same element is refused by design when it would change the page layout; the file must stay as it was
        if not ok: st += ' (clean re-save failed)'
    res[st] = res.get(st, 0) + 1
    if not ok: bad += 1; print('FAIL kill at call', k, calls[-1] if calls else '?', st)
    shutil.rmtree(w, True)
print(os.path.basename(f)[-14:], res, 'bad', bad); sys.exit(1 if bad else 0)
