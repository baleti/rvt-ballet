"""Moving a wall that has hosted/cutting family instances or dimensions is REFUSED (the writer moves only the wall record; Revit's own move of such a wall is rolled back or drags the dependents). An isolated wall still moves.
Needs local Revit-saved 2026 Autodesk Structural bases (RVT_MV_DEPS_BASE: wall 585072 with dependents; RVT_MV_ISO_BASE: isolated wall 1037167); skipped without them."""
import os, sys, subprocess, tempfile, unittest
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
DEP = os.environ.get('RVT_MV_DEPS_BASE', os.path.expanduser('~/c2x-diff/c4xaw26/base.rvt'))
ISO = os.environ.get('RVT_MV_ISO_BASE', os.path.expanduser('~/c2x-diff/c1xwiso26/base.rvt'))

def run(src, op):
    d = tempfile.mkdtemp(); out = os.path.join(d, 'o.rvt')
    r = subprocess.run([sys.executable, LAB, src, out, op], capture_output=True, text=True, cwd=os.path.dirname(LAB))
    return r, os.path.exists(out)

class MoveDeps(unittest.TestCase):
    def test_refused_with_dependents(self):
        if not (os.path.exists(DEP) and os.path.exists(LAB)): self.skipTest('no base/edit-lab')
        r, w = run(DEP, 'mv:585072:1:0:0')
        self.assertNotEqual(r.returncode, 0); self.assertFalse(w); self.assertIn('dependent', r.stdout + r.stderr)
    def test_isolated_moves(self):
        if not (os.path.exists(ISO) and os.path.exists(LAB)): self.skipTest('no base/edit-lab')
        r, w = run(ISO, 'mv:1037167:1:0:0')
        self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:]); self.assertTrue(w)

if __name__ == '__main__': unittest.main()
