"""A damaged input (64 flipped bytes inside a partition) was cloned into an 'ok' output; now REFUSED with nothing written. Fails without the check."""
import os, sys, glob, subprocess, tempfile, unittest
F = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')))
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(F, 'no corpus')
class Damaged(unittest.TestCase):
    def test_refused(self):
        with tempfile.TemporaryDirectory() as d:
            b = bytearray(open(F[0], 'rb').read()); p = len(b) // 2
            for j in range(64): b[p + j] ^= 0xFF
            s = os.path.join(d, 'c.rvt'); open(s, 'wb').write(b)
            r = subprocess.run([sys.executable, TOOL, s, os.path.join(d, 'o.rvt'), '--src', '1365188'], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('damaged', r.stdout + r.stderr); self.assertEqual(os.listdir(d), ['c.rvt'])
if __name__ == '__main__': unittest.main()
