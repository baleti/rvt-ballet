"""Deleting an existing wall must leave its id in NO Global/Latest id-list, including the long (>400 ids) sorted list (genlib2.registry_remove scanned only 400 entries back).
Autodesk sample. Marked expectedFailure until the Revit-made wall delete (tag c1xwdel) confirms that Revit removes the id from the long list too; then fix genlib2 (range(0,20000)) and drop the marker."""
import os, sys, re, struct, tempfile, unittest
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
@unittest.skipUnless(os.path.exists(F), 'no corpus')
class WallDelLatest(unittest.TestCase):
    @unittest.expectedFailure
    def test_no_leftover_id(self):
        import adiff, rvtedit
        w = 936763; pat = re.escape(struct.pack('<Q', w))
        self.assertEqual(len(re.findall(pat, adiff.graw(F, 'Global/Latest'))), 2)
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'o.rvt'); ed = rvtedit.Edit(F); ed.delete(w); ed.save(o)
            self.assertEqual(len(re.findall(pat, adiff.graw(o, 'Global/Latest'))), 0)
if __name__ == '__main__': unittest.main()
