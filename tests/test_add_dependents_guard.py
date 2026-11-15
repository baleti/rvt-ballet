"""ADD must refuse a clone source that owns dependent elements (a copy would corrupt the model) and write nothing.
Needs $RVT_ADD_SAMPLE_STRUCT24 (Autodesk Snowdon Structural 2024); $RVT_ADD_DEP_SRC defaults to column 606574 (child FamilyInstance 683291)."""
import os, sys, subprocess, tempfile, unittest
SAMPLE = os.environ.get('RVT_ADD_SAMPLE_STRUCT24'); SRC = os.environ.get('RVT_ADD_DEP_SRC', '606574')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')

@unittest.skipUnless(SAMPLE and os.path.exists(SAMPLE), 'RVT_ADD_SAMPLE_STRUCT24 not set')
class DependentsGuard(unittest.TestCase):
    def test_refuses_source_with_dependents(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt')
            r = subprocess.run([sys.executable, TOOL, SAMPLE, out, '--src', SRC], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('owns dependent', r.stdout + r.stderr)
            self.assertEqual(os.listdir(d), [])      # nothing written, no .part leftovers

if __name__ == '__main__': unittest.main()
