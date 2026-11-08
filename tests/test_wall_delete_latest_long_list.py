"""Deleting an existing wall must leave its id in NO Global/Latest id-list, including the long (>400 ids) sorted list (genlib2.registry_remove scanned only 400 entries back).
Autodesk sample. Fixed in genlib2 (scan 20000 entries) by c1x-rvtdiff 2026-11-08; Revit-made confirmation pending (c1xwdel)."""
import os, sys, re, struct, tempfile, unittest
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
@unittest.skipUnless(os.path.exists(F), 'no corpus')
class WallDelLatest(unittest.TestCase):
    def test_no_leftover_id(self):
        import adiff, rvtedit
        w = 936763; pat = re.escape(struct.pack('<Q', w))
        self.assertEqual(len(re.findall(pat, adiff.graw(F, 'Global/Latest'))), 2)
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'o.rvt'); ed = rvtedit.Edit(F); ed.delete(w); ed.save(o)
            self.assertEqual(len(re.findall(pat, adiff.graw(o, 'Global/Latest'))), 0)
    def test_instance_deep_in_long_list(self):
        import adiff, rvtedit
        raw = adiff.graw(F, 'Global/Latest'); e = struct.unpack_from('<Q', raw, 153703 + 4 + 8 * 800)[0]   # 801st id of the 942-id FamilyInstance list
        pat = re.escape(struct.pack('<Q', e)); before = len(re.findall(pat, raw))
        self.assertGreaterEqual(before, 1)
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'o.rvt'); ed = rvtedit.Edit(F); ed.delete(e); ed.save(o)
            self.assertEqual(len(re.findall(pat, adiff.graw(o, 'Global/Latest'))), 0)
if __name__ == '__main__': unittest.main()
