"""in-place edit with the backup on a DIFFERENT filesystem (SAVEGATE_BACKUPS=cache, SAVEGATE_CACHE on /dev/shm, target in the home fs): saved, backup == original, check clean, no stray files beside the target. python tests/test_inplace_crossdev.py"""
import os, sys, shutil, hashlib, subprocess, tempfile
S = os.path.expanduser("~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt")
if not os.path.exists(S) or not os.path.isdir("/dev/shm"): print("skipped"); sys.exit(0)
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "rvt-ballet")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
D = tempfile.mkdtemp(dir=os.path.expanduser("~")); C = tempfile.mkdtemp(dir="/dev/shm")
try:
    assert os.stat(D).st_dev != os.stat(C).st_dev, "same fs"
    P = D + "/ip.rvt"; shutil.copy(S, P); before = sha(P); L0 = set(os.listdir(D)) | {"gate.json"}
    open(D + "/gate.json", "w").write(chr(123) + chr(34) + "rvt" + chr(34) + ": " + chr(123) + chr(34) + "2024" + chr(34) + ": " + chr(34) + "open" + chr(34) + chr(125) + chr(125))
    env = dict(os.environ, SAVEGATE_JOURNAL=D + "/j", SAVEGATE_CACHE=C, SAVEGATE_BACKUPS="cache", RVTBALLET_ALLOW_OVERWRITE="1", SAVEGATE_GATE=D + "/gate.json")
    r = subprocess.run([BIN, "edit", P, "--in-place", "--set-string", "1365188", "Mark", "xdev"], capture_output=True, text=True, env=env, timeout=900)
    bk = [os.path.join(dp, f) for dp, _, fs in os.walk(C) for f in fs]
    okb = any(sha(b) == before for b in bk)
    stray = set(os.listdir(D)) - L0 - {"j"}
    chk = subprocess.run([BIN, "check", P], capture_output=True, text=True).returncode == 0
    ok = r.returncode == 0 and sha(P) != before and okb and chk and not stray
    print("rc", r.returncode, "saved", sha(P) != before, "backup==orig(other fs)", okb, "check", chk, "stray", stray, "OK" if ok else "FAIL", (r.stdout + r.stderr).strip()[-200:] if not ok else "")
    assert ok
finally: shutil.rmtree(D, ignore_errors=True); shutil.rmtree(C, ignore_errors=True)
