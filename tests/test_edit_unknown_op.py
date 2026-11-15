"""rvtedit.py refuses an UNKNOWN op name (exit 4, no output file). It used to ignore it and save an unedited copy ('rotate:' instead of 'rot:'), which looked like a successful edit. Autodesk HVAC 2024; skipped without corpus/edit-lab."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')

class UnknownOp(unittest.TestCase):
    def test_refused(self):
        f = glob.glob(CORPUS + '/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
        if not f or not os.path.exists(LAB): self.skipTest('no corpus/edit-lab')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 't.rvt')
            r = subprocess.run([sys.executable, LAB, f[0], out, 'rotate:1422186:30'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
            self.assertIn('unknown operation', r.stdout + r.stderr)
            self.assertFalse(os.path.exists(out))

if __name__ == '__main__': unittest.main()
