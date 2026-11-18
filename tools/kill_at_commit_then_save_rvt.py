"""kill_at_commit_then_save_rvt.py: in-place SAVE! with a real edit, child SIGKILLed at the start of commit_temp (backup done, rename not): original byte-identical; a fresh process then saves a new edit (sweeps the orphan temp). Needs ~/c3x-tmp-port4/c2025.rte (public Construction .rte). Output judged in the Revit VM by rvt_judge1 (2025 PASS, 2026-11-18)."""
import os, sys, shutil, hashlib, subprocess
H = os.path.expanduser("~/src/rvt-ballet"); src = os.path.expanduser("~/c3x-tmp-port4/c2025.rte")
w = os.path.expanduser("~/c3x-tmp-j5/k2025"); shutil.rmtree(w, True); os.makedirs(w); out = w + "/c.rte"; shutil.copy(src, out)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest(); h0 = sha(out)
CH = '''
import sys, os, signal
sys.path.insert(0, sys.argv[1])
from rvtballet import save, edit
sgm = save._import()
from savegate import atomic
real = atomic.commit_temp
def ct(*a, **k): os.kill(os.getpid(), signal.SIGKILL)
atomic.commit_temp = ct
ss = save.SaveSessions(); d = ss.doc("m1", sys.argv[2]); eid = 281147
nb, _ = edit.apply_full(d.buf, [edit.validate_op({"op": "set_string", "eid": eid, "param": "Keynote", "value": "kill me"})])
save.save_overwrite(ss, "m1", sys.argv[2], new_bytes=nb, manifest={"modified": ["el:281147"]}); print("SAVED")
'''
side = os.popen("mktemp -d").read().strip(); open(side + "/g.json", "w").write('{"rvt": {"*": "open"}}')
env = dict(os.environ, SAVEGATE_GATE=side + "/g.json", SAVEGATE_JOURNAL=side + "/j", SAVEGATE_CACHE=side + "/c", RVTBALLET_ALLOW_OVERWRITE="1", RVTBALLET_EDIT_BACKEND="rvtedit", RVTBALLET_ALLOW_LAYOUT_CHANGE="1")
r = subprocess.run([sys.executable, "-c", CH, H, out], env=env, capture_output=True, text=True)
print("rc", r.returncode, "out", r.stdout.strip()[:40], "| sha unchanged", sha(out) == h0, "| litter", sorted(x for x in os.listdir(w) if x != "c.rte"))
# second save, fresh process
CH2 = CH.split("real = atomic")[0].replace("from savegate import atomic", "") + '''
ss = save.SaveSessions(); d = ss.doc("m2", sys.argv[2])
nb, _ = edit.apply_full(d.buf, [edit.validate_op({"op": "set_string", "eid": 281147, "param": "Keynote", "value": "inplace qa"})])
save.save_overwrite(ss, "m2", sys.argv[2], new_bytes=nb, manifest={"modified": ["el:281147"]}); print("SAVED2")
'''
r = subprocess.run([sys.executable, "-c", CH2, H, out], env=env, capture_output=True, text=True)
print("second:", r.stdout.strip()[:20], r.stderr[-200:], "| changed", sha(out) != h0, "| litter", sorted(x for x in os.listdir(w) if x != "c.rte"))
