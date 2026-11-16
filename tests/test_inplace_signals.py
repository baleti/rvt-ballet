"""SIGTERM/SIGINT/SIGHUP at several moments of an in-place save: afterwards the target is either byte-identical to the original or a complete file (check clean) with backup == original; no .tmp leftovers beside it. python tests/test_inplace_signals.py"""
import os, sys, shutil, hashlib, subprocess, tempfile, time, signal
S = os.path.expanduser("~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt")
if not os.path.exists(S): print("skipped"); sys.exit(0)
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "rvt-ballet")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
CASES = [(signal.SIGTERM, d) for d in (3, 25, 55, 85)] + [(signal.SIGINT, d) for d in (25, 55)] + [(signal.SIGHUP, 40)]
T = tempfile.mkdtemp(); fails = []
try:
    for sg, delay in CASES:
        D = "%s/%s_%d" % (T, sg.name, delay); os.makedirs(D); P = D + "/ip.rvt"; shutil.copy(S, P); before = sha(P)
        open(D + "/gate.json", "w").write(chr(123) + chr(34) + "rvt" + chr(34) + ": " + chr(123) + chr(34) + "2024" + chr(34) + ": " + chr(34) + "open" + chr(34) + chr(125) + chr(125))
        env = dict(os.environ, SAVEGATE_JOURNAL=D + "/j", SAVEGATE_CACHE=D + "/c", RVTBALLET_ALLOW_OVERWRITE="1", SAVEGATE_GATE=D + "/gate.json")
        p = subprocess.Popen([BIN, "edit", P, "--in-place", "--set-string", "1365188", "Mark", "sig"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        time.sleep(delay)
        done = p.poll() is not None
        if not done:
            try: os.killpg(p.pid, sg)
            except ProcessLookupError: pass
        try: p.wait(timeout=60)
        except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL); p.wait()
        time.sleep(1)
        saved = sha(P) != before
        bk = [os.path.join(dp, f) for dp, _, fs in os.walk(D) for f in fs if ".savegate" in dp and os.path.getsize(os.path.join(dp, f)) > 1e6]
        okb = (not saved) or any(sha(b) == before for b in bk)
        chk = subprocess.run([BIN, "check", P], capture_output=True, text=True).returncode == 0
        tmp = [f for f in os.listdir(D) if f not in ("ip.rvt", "gate.json", "j", "c") and not f.startswith(".")]
        hid = [f for f in os.listdir(D) if f.startswith(".") and f != ".ip.rvt.savegate"]
        ok = okb and chk and not tmp
        print(sg.name, delay, "finished-before-signal" if done else "signalled", "rc", p.returncode, "saved", saved, "backup==orig", okb, "check", chk, "visible-stray", tmp, "hidden", hid, "OK" if ok else "FAIL", flush=True)
        if not ok: fails.append((sg.name, delay))
finally: shutil.rmtree(T, ignore_errors=True)
assert not fails, fails
print("signal cases ok")
