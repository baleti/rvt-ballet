"""Two add-wall calls in sequence (second on the first's output) give distinct new ids, +1 element and +1 wall each time; source untouched. Reader check only (Revit verdict via VM suite). Autodesk sample."""
import os, sys, subprocess, tempfile, unittest, hashlib
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_aw_auto.py')
@unittest.skipUnless(os.path.exists(F), 'no corpus')
class Chained(unittest.TestCase):
    def test_two_adds(self):
        import rvt_geometry as G
        h0 = hashlib.sha256(open(F, 'rb').read()).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            a1, a2 = os.path.join(d, 'a1.rvt'), os.path.join(d, 'a2.rvt')
            for s, o, y in ((F, a1, '0'), (a1, a2, '5')):
                r = subprocess.run([sys.executable, TOOL, s, o, '0', y, '10', y], capture_output=True, text=True); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            ix = [G.file_geometry_index(f) for f in (F, a1, a2)]
            self.assertEqual([len(i) for i in ix], [len(ix[0]), len(ix[0]) + 1, len(ix[0]) + 2])
            w = [{e for e, v in i.items() if str(v) == 'SWall'} for i in ix]
            self.assertEqual(len(w[1] - w[0]), 1); self.assertEqual(len(w[2] - w[1]), 1); self.assertTrue(w[0] < w[1] < w[2])
        self.assertEqual(h0, hashlib.sha256(open(F, 'rb').read()).hexdigest())
if __name__ == '__main__': unittest.main()
