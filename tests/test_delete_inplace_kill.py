"""SIGKILL of an in-place SAVE! of a delete (private copy) at several points: the source file afterwards is either byte-identical to the original or a complete file that parses and lacks the target; never a half-written file.
Needs $RVT_DEL_KILL_SAMPLE (Autodesk sample) and $RVT_DEL_KILL_EID (a deletable FamilyInstance id)."""
import os, sys, glob, time, signal, hashlib, tempfile, subprocess, unittest
S = os.environ.get('RVT_DEL_KILL_SAMPLE'); E = os.environ.get('RVT_DEL_KILL_EID')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvtsave_inplace_delete.py')
import fnmatch
def _find(d, pat):
    return [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if fnmatch.fnmatch(f, pat)]  # dot-files included (glob skips them)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
@unittest.skipUnless(S and E and os.path.exists(S), 'RVT_DEL_KILL_SAMPLE/EID not set')
class T(unittest.TestCase):
    def test_kill_points(self): self._run('*.sgtmp', (0.0, 0.3, 1.0, 2.5, 'gone'))
    def test_kill_during_backup(self): self._run('*.part', (0.0, 0.2, 0.6, 'gone'))
    def _run(self, pat, delays):
        h0 = sha(S); bad = []; seen = []
        for delay in delays:
            with tempfile.TemporaryDirectory() as d:
                env = dict(os.environ, TMPDIR=d, DEL_EID=E)
                p = subprocess.Popen([sys.executable, TOOL, S], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                t0 = time.time(); tmpseen = None
                while p.poll() is None and time.time() - t0 < 900:
                    if _find(d, pat):
                        tmpseen = tmpseen or time.time()
                        if delay != 'gone' and time.time() - tmpseen >= delay: break
                    elif tmpseen and delay == 'gone': time.sleep(0.02); break
                    time.sleep(0.02)
                if p.poll() is not None: seen.append((delay, 'finished-before-kill')); continue
                p.send_signal(signal.SIGKILL); p.wait()
                for f in glob.glob(d + '/*/p.rvt'):
                    if sha(f) == h0: seen.append((delay, 'original')); continue
                    sys.path.insert(0, os.path.expanduser('~/src/savegate'))
                    from savegate import rvt_elements as R
                    try: ok = int(E) not in R.elements(open(f, 'rb').read())
                    except Exception: ok = False
                    seen.append((delay, 'complete' if ok else 'BAD'))
                    if not ok: bad.append(delay)
        print('KILL_OUTCOMES', seen)
        self.assertEqual(bad, [], 'source half-written after kill at these delays')
if __name__ == '__main__': unittest.main()
