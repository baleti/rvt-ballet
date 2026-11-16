"""prototype tools/rvt_astring_create_proto.py on Snowdon Structural 2024 (Autodesk sample): Comments created on never-set walls 585174/585255 must reproduce Revit's own record
(witness c4xcm2: record entries byte-identical, tag 3021, 24 B growth), refuse an element that already has the set pointer, and leave the source untouched. Skips when the sample/witness is absent."""
import os, subprocess, sys, tempfile, hashlib, unittest
S = '~/c5x-link/al/Snowdon Towers Sample Structural.rvt'; W = os.path.expanduser('~/c2x-diff/c4xcm2/after.rvt')
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_astring_create_proto.py')
def run(*a): return subprocess.run([sys.executable, T, *a], capture_output=True, text=True)
@unittest.skipUnless(os.path.exists(S) and os.path.exists(W), 'sample or Revit witness absent')
class T_(unittest.TestCase):
    def test_matches_revit(self):
        sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research')]
        import rvtedit
        h0 = hashlib.sha256(open(S, 'rb').read()).hexdigest(); o = os.path.join(tempfile.mkdtemp(), 'o.rvt')
        p = run(S, o, '585174', 'Comments', 'C4Y'); self.assertEqual(p.returncode, 0, p.stderr[-300:])
        def ent(f):
            ed = rvtedit.Edit(f); return [(l[1], bytes(ed.g.bj[l[2]:l[3]])) for l in ed.g.e.trace(585174)[3]]
        self.assertEqual(ent(o), ent(W)); self.assertEqual(h0, hashlib.sha256(open(S, 'rb').read()).hexdigest())
    def test_refuses_existing(self):
        o = os.path.join(tempfile.mkdtemp(), 'o.rvt'); p = run(W, o, '585174', 'Comments', 'X')
        self.assertNotEqual(p.returncode, 0); self.assertFalse(os.path.exists(o)); self.assertIn('refused', p.stdout + p.stderr)
if __name__ == '__main__': unittest.main()
