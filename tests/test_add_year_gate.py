"""ADD on a Revit 2025+ file is refused (the 2025 HVAC FI ADD build failed to open in the Revit VM, CArchiveException 105); nothing is written.
Needs $RVT_ADD_SAMPLE_2025 (Autodesk Snowdon HVAC 2025) and $RVT_ADD_SRC_2025 (e.g. 1377544)."""
import os, sys, subprocess, tempfile, unittest
S = os.environ.get('RVT_ADD_SAMPLE_2025'); SRC = os.environ.get('RVT_ADD_SRC_2025', '1377544')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(S and os.path.exists(S), 'RVT_ADD_SAMPLE_2025 not set')
class T(unittest.TestCase):
    def test_refused(self):
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'a.rvt')
            r = subprocess.run([sys.executable, TOOL, S, o, '--src', SRC], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('no Revit-open PASS', r.stderr + r.stdout); self.assertFalse(os.path.exists(o))
if __name__ == '__main__': unittest.main()
