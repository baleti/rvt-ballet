"""A source that sits in no Global/Latest id-list is refused with a plain message (was a bare AssertionError traceback); nothing written. 2017 rst_advanced, source 132597 (found by the c3x-rvtadd corpus sweep)."""
import os, sys, subprocess, tempfile, unittest
F = os.path.expanduser('~/rvt-research/corpus/2017/01_rst_advanced_sample_project.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(os.path.exists(F), 'no corpus')
class NoIdList(unittest.TestCase):
    def test_refused_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt'); r = subprocess.run([sys.executable, TOOL, F, out, '--src', '132597'], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('no Global/Latest id-list', r.stdout + r.stderr); self.assertNotIn('Traceback', r.stderr); self.assertEqual(os.listdir(d), [])
if __name__ == '__main__': unittest.main()
