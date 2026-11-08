"""edit-lab rvtedit.py on a damaged input (64 flipped bytes) printed 'saved'; now REFUSED rc 2, nothing written."""
import os, sys, glob, subprocess, tempfile, unittest
F = glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
@unittest.skipUnless(F and os.path.exists(LAB), 'no corpus/edit-lab')
class Damaged(unittest.TestCase):
    def test_refused(self):
        with tempfile.TemporaryDirectory() as d:
            b = bytearray(open(F[0], 'rb').read()); p = len(b) // 2
            for j in range(64): b[p + j] ^= 0xFF
            s = os.path.join(d, 'c.rvt'); open(s, 'wb').write(b)
            r = subprocess.run([sys.executable, LAB, s, os.path.join(d, 'o.rvt'), 'at:1487400:1447768:1:1'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 2); self.assertIn('damaged', r.stderr); self.assertEqual(os.listdir(d), ['c.rvt'])
if __name__ == '__main__': unittest.main()
