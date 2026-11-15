"""ADD must refuse a project with more than one non-empty Partitions stream (Revit VM 2026-11-15: 2023 Arch_Link_Model column clone = CorruptModelException).
Local-only corpus sample; skipped when absent."""
import os, subprocess, sys, unittest
SEED = os.path.expanduser('~/rvt-research/corpus/2023/38_Arch_Link_Model.rvt')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')

class T(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(SEED), 'sample not present')
    def test_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt')
            r = subprocess.run([sys.executable, TOOL, SEED, out, '--src', '182667'], capture_output=True, text=True, timeout=900)
            self.assertNotEqual(r.returncode, 0); self.assertIn('non-empty Partitions', r.stdout + r.stderr)
            self.assertFalse(os.path.exists(out))
if __name__ == '__main__': unittest.main()
