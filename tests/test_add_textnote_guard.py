"""TextNote ADD (edit-lab 'tn' op) refuses empty/blank text and control characters, writes no file. Autodesk HVAC 2024; skipped without corpus/edit-lab."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')

class TnGuard(unittest.TestCase):
    def test_refused(self):
        f = glob.glob(CORPUS + '/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
        if not f or not os.path.exists(LAB): self.skipTest('no corpus/edit-lab')
        for t in ('', '  ', 'a\nb', 'a\tb'):
            with tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, 't.rvt')
                r = subprocess.run([sys.executable, LAB, f[0], out, 'tn:1422186:5:5:' + t], capture_output=True, text=True, cwd=os.path.dirname(LAB))
                self.assertIn('REFUSED', r.stdout + r.stderr, repr(t)); self.assertFalse(os.path.exists(out))

if __name__ == '__main__': unittest.main()
