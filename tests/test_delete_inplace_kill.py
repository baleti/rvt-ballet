"""SIGKILL of an in-place SAVE! of a delete (private copy) at several points: the source file afterwards is either byte-identical to the original or a complete file that parses and lacks the target; never a half-written file.
Needs $RVT_DEL_KILL_SAMPLE (Autodesk sample) and $RVT_DEL_KILL_EID (a deletable FamilyInstance id)."""
import os, sys, glob, time, signal, hashlib, tempfile, subprocess, unittest
S = os.environ.get('RVT_DEL_KILL_SAMPLE'); E = os.environ.get('RVT_DEL_KILL_EID')
WRAP = os.path.join(os.path.dirname(__file__), '..', 'tools', '_kill_at_step.py')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvtsave_inplace_delete.py')
import fnmatch
def _find(d, pat):
    return [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if fnmatch.fnmatch(f, pat)]  # dot-files included (glob skips them)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
@unittest.skipUnless(S and E and os.path.exists(S), 'RVT_DEL_KILL_SAMPLE/EID not set')
class T(unittest.TestCase):
    def test_kill_points(self):
        """deterministic: SIGKILL at the exact savegate steps (hook), not by polling"""
        h0 = sha(S); bad = []; seen = []
        sys.path.insert(0, os.path.expanduser('~/src/savegate'))
        from savegate import rvt_elements as R
        for at in ('tmp_written', 'before_replace', 'after_replace'):
            with tempfile.TemporaryDirectory() as d:
                env = dict(os.environ, TMPDIR=d, DEL_EID=E, KILL_AT=at)
                p = subprocess.run([sys.executable, WRAP, S], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3000)
                fs = glob.glob(d + '/*/p.rvt')
                if p.returncode != -signal.SIGKILL or not fs: seen.append((at, 'NOT-KILLED rc=%s' % p.returncode)); bad.append(at); continue
                f = fs[0]
                if sha(f) == h0: seen.append((at, 'original')); continue
                try: ok = int(E) not in R.elements(open(f, 'rb').read())
                except Exception: ok = False
                seen.append((at, 'complete' if ok else 'BAD'))
                if not ok: bad.append(at)
        print('KILL_OUTCOMES', seen)
        self.assertEqual(bad, [], 'source half-written or hook never fired: %s' % seen)
if __name__ == '__main__': unittest.main()
