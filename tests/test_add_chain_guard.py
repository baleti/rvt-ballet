"""A 2nd ADD on top of an ADD output is refused (Revit VM 2026-11-16: the earlier added element is silently dropped). Single ADD must still build. Local-only corpus sample; skipped when absent."""
import os, subprocess, sys, tempfile, unittest
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')
F = os.path.expanduser('~/rvt-research/corpus/2023/36_rst_basic_sample_project.rvt')
class T(unittest.TestCase):
    def test_second_add_refused(self):
        if not os.path.exists(F): self.skipTest('sample not present')
        e = dict(os.environ, RVT_ADD_PROFILE_B_MULTI='1'); e.pop('RVT_ADD_CHAIN_FORCE', None)
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'a.rvt'), os.path.join(d, 'b.rvt')
            r = subprocess.run([sys.executable, TOOL, F, a, '--src', '512451'], capture_output=True, text=True, timeout=1800, env=e)
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            r = subprocess.run([sys.executable, TOOL, a, b, '--src', '512451'], capture_output=True, text=True, timeout=1800, env=e)
            self.assertNotEqual(r.returncode, 0); self.assertIn('already carries an element added', r.stdout + r.stderr)
            self.assertFalse(os.path.exists(b))
if __name__ == '__main__': unittest.main()
