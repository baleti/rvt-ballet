"""c8x-rvtjudge6 2026-11-18: gate-negative regression on a PUBLIC Autodesk sample (2025 .rte, path in RVT_GATE_SAMPLE, default ~/c3x-tmp-port4/c2025.rte; skipped if absent).
One valid Mark edit of el 1319; (a) 12 tampered copies (bit flips, truncate, append, zero block) must ALL be refused with the original byte-identical;
(b) a valid second edit of an UNDECLARED element must be refused; (c) known gap, asserted so a fix is noticed: two params on the DECLARED element are accepted (per-element granularity)."""
import os, sys, shutil, hashlib, random, tempfile
_T = tempfile.mkdtemp(); os.environ["SAVEGATE_JOURNAL"] = _T + "/j"; os.environ["SAVEGATE_CACHE"] = _T + "/c"; os.environ["RVTBALLET_ALLOW_OVERWRITE"] = "1"; os.environ["RVTBALLET_EDIT_BACKEND"] = "rvtedit"
open(_T + "/g.json", "w").write('{"rvt": {"*": "open"}}'); os.environ["SAVEGATE_GATE"] = _T + "/g.json"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.expanduser(os.environ.get("RVT_GATE_SAMPLE", "~/c3x-tmp-port4/c2025.rte"))
if not os.path.exists(SRC): print("SKIP no sample"); sys.exit(0)
from rvtballet import save, edit
S = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
p = _T + "/t.rte"; shutil.copy(SRC, p); h0 = S(p); EID = 1319
def build(ops):
    ss = save.SaveSessions(); d = ss.doc("m", p); nb, _ = edit.apply_full(d.buf, [edit.validate_op(o) for o in ops]); return bytes(nb)
mark = {"op": "set_string", "eid": EID, "param": "Mark", "value": "gate neg"}
nb = build([mark]); n = len(nb); random.seed(68); cases = []
for _ in range(8):
    o = random.randrange(n); b = bytearray(nb); b[o] ^= 1 << random.randrange(8); cases.append(("flip@%d" % o, bytes(b)))
cases += [("truncate", nb[:-100]), ("append", nb + b"\x00" * 16), ("zero4k", nb[:n // 2] + b"\x00" * 4096 + nb[n // 2 + 4096:]), ("empty-tail", nb[:n - 4096])]
def attempt(label, data, manifest):
    ss = save.SaveSessions(); ss.doc("m", p)
    try: save.save_overwrite(ss, "m", p, new_bytes=data, manifest=manifest); return True
    except Exception: return False
for label, data in cases:
    assert not attempt(label, data, {"modified": ["el:%d" % EID]}), "ESCAPE: tampered output accepted: " + label
    assert S(p) == h0, "original changed after refused " + label
und = build([mark, {"op": "set_string", "eid": 1307, "param": "Comments", "value": "undeclared"}])
assert not attempt("undeclared", und, {"modified": ["el:%d" % EID]}), "ESCAPE: undeclared element edit accepted"; assert S(p) == h0
two = build([{"op": "set_string", "eid": 1307, "param": "Comments", "value": "a"}, {"op": "set_string", "eid": 1307, "param": "Mark", "value": "b"}])
gap = attempt("two-params", two, {"modified": ["el:1307"]})
print("tampered refused", len(cases), "| undeclared refused | KNOWN GAP two params on declared element accepted:", gap)
