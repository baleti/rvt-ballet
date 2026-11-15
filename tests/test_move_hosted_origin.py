"""Moving a hosted FamilyInstance (window 593207, Autodesk Snowdon Facades 2024 original): m_instOrigin is host-relative (0,0,0) there, Trf.m_or is the world position. The writer must shift Trf.m_or ONLY (it used to add the world delta to m_instOrigin too, leaving the two fields inconsistent).
Skipped without the local corpus file / edit-lab."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

class MoveHosted(unittest.TestCase):
    def test_only_world_origin_moves(self):
        f = glob.glob(CORPUS + '/2024/46_Snowdon_Towers_Sample_Facades.rvt')
        if not f or not os.path.exists(LAB): self.skipTest('no corpus/edit-lab')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt')
            r = subprocess.run([sys.executable, LAB, f[0], out, 'mv:593207:0.5:0:0'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:]); self.assertTrue(os.path.exists(out))
            import rvt_diff
            rep = rvt_diff.diff(f[0], out, True, 50, [593207])
            row = [c for c in rep['changed'] if c['id'] == 593207][0]
            names = [x['field'] for x in row['fields']]
            self.assertIn('Trf.m_or#1', names)
            self.assertNotIn('FamilyInstance.m_instOrigin#1', names)

if __name__ == '__main__': unittest.main()
