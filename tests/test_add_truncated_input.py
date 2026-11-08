"""A truncated / empty input to rvt_add_clone is a plain REFUSED (rc 2, no traceback), nothing written beside it."""
import os, sys, glob, subprocess, tempfile, unittest
F = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*.rvt')))
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(F, 'no corpus')
class Trunc(unittest.TestCase):
    def test_refused(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 's.rvt'); open(src, 'wb').write(open(F[0], 'rb').read(3000000))
            emp = os.path.join(d, 'e.rvt'); open(emp, 'wb').close()
            for s in (src, emp):
                r = subprocess.run([sys.executable, TOOL, s, os.path.join(d, 'o.rvt'), '--src', '1'], capture_output=True, text=True)
                self.assertEqual(r.returncode, 2); self.assertIn('REFUSED', r.stderr); self.assertNotIn('Traceback', r.stderr)
            self.assertEqual(sorted(os.listdir(d)), ['e.rvt', 's.rvt'])
if __name__ == '__main__': unittest.main()
