"""rvt_aw_auto refuses degenerate walls (zero/near-zero length, zero/negative/huge height, NaN/inf/absurd coordinates) before touching any file."""
import os, sys, subprocess, tempfile, unittest
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_aw_auto.py')

class AwGuard(unittest.TestCase):
    def test_refused(self):
        for a in (('0','0','0','0','10'), ('0','0','0.001','0','10'), ('0','0','5','0','0'), ('0','0','5','0','-10'), ('0','0','nan','0','10'),
                  ('0','0','inf','0','10'), ('0','0','5','0','100000'), ('0','0','1e9','0','10'), ('0','0','x','0','10')):
            with tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, 'o.rvt')
                r = subprocess.run([sys.executable, TOOL, os.path.join(d, 'nosuch.rvt'), out, *a], capture_output=True, text=True)
                self.assertNotEqual(r.returncode, 0, a); self.assertIn('REFUSED', r.stdout + r.stderr, a); self.assertFalse(os.path.exists(out))

if __name__ == '__main__': unittest.main()
