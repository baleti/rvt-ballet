"""ADD must refuse a curtain-grid cell source (its clone made a file Revit fails to open). Needs $RVT_ADD_SAMPLE_RME23 (Autodesk rme_basic 2023 sample); $RVT_ADD_CURTAIN_SRC defaults to door 573615."""
import os, sys, subprocess, tempfile, unittest
SAMPLE = os.environ.get('RVT_ADD_SAMPLE_RME23'); SRC = os.environ.get('RVT_ADD_CURTAIN_SRC', '573615')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')

@unittest.skipUnless(SAMPLE and os.path.exists(SAMPLE), 'RVT_ADD_SAMPLE_RME23 not set')
class CurtainGuard(unittest.TestCase):
    def test_refuses_curtain_cell_source(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt')
            r = subprocess.run([sys.executable, TOOL, SAMPLE, out, '--src', SRC], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('curtain-grid cell', r.stdout + r.stderr)
            self.assertEqual(os.listdir(d), [])

if __name__ == '__main__': unittest.main()
