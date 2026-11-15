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

    def test_header_outline_min_and_instorigin_like_revit(self):
        """Revit-made +0.5 x move (2024_house3.rte door 301609): header Outline.m_minmax min x 16.3333 -> 16.8333 (the min corner has a ~1e-16 z that a noise filter skipped) and FamilyInstance.m_instOrigin stays 18.0 (host-relative)."""
        if not os.path.exists(SCENE) or not os.path.exists(LAB): self.skipTest('no scene/edit-lab')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rte')
            r = subprocess.run([sys.executable, LAB, SCENE, out, 'mv:301609:0.5:0:0'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            code = "import sys,struct;sys.path.insert(0,'.');import rvtedit;T=rvtedit.Edit(sys.argv[1]).g.template(301609);hl={n:o for n,o,e,_ in T['hlog']};print(struct.unpack_from('<6d',T['hdr'],hl['Outline.m_minmax'])[0])"
            q = subprocess.run([sys.executable, '-c', code, out], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertAlmostEqual(float(q.stdout.strip().splitlines()[-1]), 16.833333333333, places=6, msg=q.stderr[-300:])
            import rvt_diff
            rep = rvt_diff.diff(SCENE, out, True, 50, [301609])
            names = [x['field'] for c in rep['changed'] if c['id'] == 301609 for x in c['fields']]
            self.assertNotIn('FamilyInstance.m_instOrigin#1', names)

    def test_zone_item_corners_shift_like_revit(self):
        """Zone item of door 301609 holds outline corner triples whose z is ~-8.9e-16; Revit's move shifts them (x 16.3333 -> 16.8333 at item offsets 48 and 96), a 1e-9 noise filter skipped them."""
        if not os.path.exists(SCENE) or not os.path.exists(LAB): self.skipTest('no scene/edit-lab')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rte')
            r = subprocess.run([sys.executable, LAB, SCENE, out, 'mv:301609:0.5:0:0'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            code = "import sys,struct;sys.path.insert(0,'.');import rvtedit;g=rvtedit.Edit(sys.argv[1]).g;z=g.locate(301609)['zone'];it=bytes(g.bj[z[0][0]+4:z[0][0]+z[0][1]]);print(struct.unpack_from('<d',it,48)[0],struct.unpack_from('<d',it,96)[0])"
            q = subprocess.run([sys.executable, '-c', code, out], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            a, b = map(float, q.stdout.strip().splitlines()[-1].split())
            self.assertAlmostEqual(a, 16.833333333333, places=6, msg=q.stderr[-300:]); self.assertAlmostEqual(b, 16.833333333333, places=6)

if __name__ == '__main__': unittest.main()
