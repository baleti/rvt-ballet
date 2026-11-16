"""FamilyInstance ADD (rvt_add_clone, edit engine) on Autodesk samples of several years: main reader must see exactly +1 record
(new id = ElemTable counter + 1), nothing removed or changed. Offline only; Revit verdicts are recorded separately.
Needs the sample corpus in $RVT_CORPUS (default ~/rvt-research/corpus); skipped when absent."""
import os, sys, subprocess, tempfile, unittest, glob
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CASES = [(2020, '18_rst_basic_sample_project.rvt', 512451), (2021, '26_Arch_Link_Model.rvt', 172320),
         (2022, '32_Arch_Link_Model.rvt', 172320), (2023, '38_Arch_Link_Model.rvt', 172320)]

class AddYears(unittest.TestCase):
    def test_years(self):
        from rvtballet import reader
        ran = 0
        for y, name, src in CASES:
            f = glob.glob('%s/%d/%s' % (CORPUS, y, name))
            if not f: continue
            with self.subTest(year=y), tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, 'o.rvt')
                r = subprocess.run([sys.executable, TOOL, f[0], out, '--src', str(src)], capture_output=True, text=True, env=dict(os.environ, RVT_ADD_EDITENGINE='1', RVT_ADD_EDITENGINE_FORCE='1', RVT_ADD_LAYOUT_FORCE='1', RVT_ADD_MULTIPART_FORCE='1'))
                self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
                a = reader.load(f[0])['recs']; b = reader.load(out)['recs']
                new = [k for k in b if k not in a]; gone = [k for k in a if k[0] != 0 and 'error' not in a[k] and k not in b]
                chg = [k for k in a if k in b and not (k[0] == 0 or 'error' in a[k]) and a[k] != b[k]]
                self.assertEqual(len(new), 1, new[:3]); self.assertEqual(new[0][1], 'FamilyInstance')
                self.assertFalse(gone); self.assertFalse(chg); ran += 1
        if not ran: self.skipTest('no corpus')

if __name__ == '__main__': unittest.main()
