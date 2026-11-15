"""Moving a hosted door along its wall must also shift InsertableInst.m_hostParam (distance along the host wall), as Revit's own MoveElement does (synthetic write-lab scene 2024_house3.rte, door 301609: 18.0 -> 18.5 with Trf.m_or). Skipped without the local scene / edit-lab. Run with python -m unittest."""
import os, sys, subprocess, tempfile, unittest
SCENE = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

class HostParam(unittest.TestCase):
    def test_hostparam_follows_move(self):
        if not os.path.exists(SCENE) or not os.path.exists(LAB): self.skipTest('no scene/edit-lab')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rte')
            r = subprocess.run([sys.executable, LAB, SCENE, out, 'mv:301609:0.5:0:0'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            import rvt_diff
            rep = rvt_diff.diff(SCENE, out, True, 50, [301609])
            row = [c for c in rep['changed'] if c['id'] == 301609][0]
            fl = {x['field']: x for x in row['fields']}
            self.assertIn('Trf.m_or#1', fl)
            self.assertIn('InsertableInst.m_hostParam#1', fl)

if __name__ == '__main__': unittest.main()
