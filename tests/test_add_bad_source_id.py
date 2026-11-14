"""ADD with a --src id that does not exist (or is not an element) is refused with a plain message, nothing written. 2024 Snowdon HVAC sample."""
import os, sys, subprocess, tempfile, unittest
F = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(os.path.exists(F), 'no corpus')
class BadSrc(unittest.TestCase):
    def test_refused(self):
        for sid in ('1', '999999999', '-5'):
            with tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, 'o.rvt'); r = subprocess.run([sys.executable, TOOL, F, out, '--src', sid], capture_output=True, text=True)
                self.assertNotEqual(r.returncode, 0, sid); self.assertNotIn('Traceback', r.stderr, sid); self.assertEqual(os.listdir(d), [], sid)
if __name__ == '__main__': unittest.main()
