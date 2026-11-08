"""Rotating an existing wall is not implemented (curve/profile/outline need a Revit-made reference diff): it must be REFUSED, not half-done.
Autodesk sample only. Added by c1x-rvtdiff 2026-11-08."""
import os, sys, tempfile, unittest
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
@unittest.skipUnless(os.path.exists(F), 'no corpus')
class WallRotateRefused(unittest.TestCase):
    def test_refused_no_output(self):
        import rvtedit
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'o.rvt'); ed = rvtedit.Edit(F)
            with self.assertRaises(NotImplementedError): ed.rotate(936763, 90)
            self.assertFalse(os.path.exists(o))
if __name__ == '__main__': unittest.main()
