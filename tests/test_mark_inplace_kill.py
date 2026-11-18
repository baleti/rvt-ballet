"""SIGKILL of an in-place SAVE! of a Mark (set_string) edit at the exact savegate steps (tmp_written, before_replace, after_replace) on a private copy of a public Autodesk 2024 sample: afterwards the source is byte-identical to the original or a complete file (passes savegate source_damage); never half-written. Needs the public corpus ~/rvt-research/corpus/2024."""
import os, sys, glob, signal, hashlib, tempfile, subprocess, unittest
S = os.path.expanduser(os.environ.get("RVT_MARK_KILL_SAMPLE", "~/rvt-research/corpus/2024/47_Snowdon_Towers_Sample_Site.rvt"))
WRAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "_kill_at_step_mark.py")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
@unittest.skipUnless(os.path.exists(S), "public sample absent")
class T(unittest.TestCase):
    def test_kill_points(self):
        sys.path.insert(0, os.path.expanduser("~/src/savegate"))
        from savegate.adapters import RvtAdapter
        h0 = sha(S); bad = []; seen = []
        for at in ("tmp_written", "before_replace", "after_replace"):
            with tempfile.TemporaryDirectory() as d:
                p = subprocess.run([sys.executable, WRAP, S], env=dict(os.environ, TMPDIR=d, KILL_AT=at), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3000)
                fs = glob.glob(d + "/*/p.rvt")
                if p.returncode != -signal.SIGKILL or not fs: seen.append((at, "NOT-KILLED rc=%s" % p.returncode)); bad.append(at); continue
                f = fs[0]
                if sha(f) == h0: seen.append((at, "original")); continue
                dm = RvtAdapter().source_damage(open(f, "rb").read())
                seen.append((at, "complete" if not dm else "BAD"))
                if dm: bad.append(at)
        print("KILL_OUTCOMES", seen)
        self.assertEqual(bad, [], "half-written or hook never fired: %s" % seen)
if __name__ == "__main__": unittest.main()
