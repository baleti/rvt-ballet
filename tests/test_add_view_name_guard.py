"""View ADD (edit-lab 'av' op) refuses empty/forbidden names fast and duplicate names (case-insensitive) after listing existing views (~90 s; RVT_SLOW=1).
Autodesk HVAC 2024; skipped without corpus/edit-lab. Existing view 9948 is named 'L2'."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')

def run(op):
    f = glob.glob(CORPUS + '/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
    if not f or not os.path.exists(LAB): raise unittest.SkipTest('no corpus/edit-lab')
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, 't.rvt')
        r = subprocess.run([sys.executable, LAB, f[0], out, op], capture_output=True, text=True, cwd=os.path.dirname(LAB))
        return r, os.path.exists(out)

class ViewNames(unittest.TestCase):
    def test_forbidden(self):
        for n in ('', ' ', 'a|b', 'a{b', 'a<b', 'a?b'):
            r, ex = run('av:32:' + n)
            self.assertIn('REFUSED', r.stderr + r.stdout, repr(n)); self.assertFalse(ex)
    @unittest.skipUnless(os.environ.get('RVT_SLOW'), 'slow (~90 s)')
    def test_duplicate(self):
        r, ex = run('av:32:l2'); self.assertIn('already exists', r.stderr + r.stdout); self.assertFalse(ex)

if __name__ == '__main__': unittest.main()
