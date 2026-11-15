"""SIGKILL of an in-place SAVE! of a delete (private copy) at several points: the source file afterwards is either byte-identical to the original or a complete file that parses and lacks the target; never a half-written file.
Needs $RVT_DEL_KILL_SAMPLE (Autodesk sample) and $RVT_DEL_KILL_EID (a deletable FamilyInstance id)."""
import os, sys, glob, time, signal, hashlib, tempfile, subprocess, unittest
S = os.environ.get('RVT_DEL_KILL_SAMPLE'); E = os.environ.get('RVT_DEL_KILL_EID')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvtsave_inplace_delete.py')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
@unittest.skipUnless(S and E and os.path.exists(S), 'RVT_DEL_KILL_SAMPLE/EID not set')
class T(unittest.TestCase):
    def test_kill_points(self):
        h0 = sha(S); bad = []
        for delay in (3, 8, 15, 30, 60):
            with tempfile.TemporaryDirectory() as d:
                env = dict(os.environ, TMPDIR=d, DEL_EID=E)
                p = subprocess.Popen([sys.executable, TOOL, S], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(delay)
                if p.poll() is not None: continue
                p.send_signal(signal.SIGKILL); p.wait()
                for f in glob.glob(d + '/*/p.rvt'):
                    if sha(f) == h0: continue
                    sys.path.insert(0, os.path.expanduser('~/src/savegate'))
                    from savegate import rvt_elements as R
                    try: ok = int(E) not in R.elements(open(f, 'rb').read())
                    except Exception: ok = False
                    if not ok: bad.append(delay)
        self.assertEqual(bad, [], 'source half-written after kill at these delays')
if __name__ == '__main__': unittest.main()
