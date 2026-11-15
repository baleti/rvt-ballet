"""Moving a curve-driven FamilyInstance (joined beam) is REFUSED: Revit's own +1 ft move lengthens the beam, changes setbacks and swaps in a new derived symbol, the writer would only shift the origin. A column (no curve driver) still moves.
Needs the local Revit-saved 2026 Autodesk Structural base (RVT_MV_DEPS_BASE: beam 606873, column 606069); skipped without it."""
import os, sys, subprocess, tempfile, unittest
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
BASE = os.environ.get('RVT_MV_DEPS_BASE', os.path.expanduser('~/c2x-diff/c4xaw26/base.rvt'))

def run(op):
    d = tempfile.mkdtemp(); out = os.path.join(d, 'o.rvt')
    r = subprocess.run([sys.executable, LAB, BASE, out, op], capture_output=True, text=True, cwd=os.path.dirname(LAB))
    return r, os.path.exists(out)

class MoveCurveDriven(unittest.TestCase):
    def test_beam_refused(self):
        if not (os.path.exists(BASE) and os.path.exists(LAB)): self.skipTest('no base/edit-lab')
        r, w = run('mv:606873:1:0:0')
        self.assertNotEqual(r.returncode, 0); self.assertFalse(w); self.assertIn('curve-driven', r.stdout + r.stderr)
    def test_column_moves(self):
        if not (os.path.exists(BASE) and os.path.exists(LAB)): self.skipTest('no base/edit-lab')
        r, w = run('mv:606069:1:0:0')
        self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:]); self.assertTrue(w)

if __name__ == '__main__': unittest.main()
