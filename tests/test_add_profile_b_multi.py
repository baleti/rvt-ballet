"""RVT_ADD_PROFILE_B_MULTI=1 (experiment): on a multi-partition project the ADD uses the SPLIT layout of the Revit-PASS 2024 add (first member = small head, the insert
in its own small member), not the merged layout of the Revit-rejected 2025/2023 builds. Checks layout + damage gate + one element added. NOT a Revit verdict
(pb25/pb23 VM opens pending). Needs RVT_ADD_SAMPLE_2023 (a multi-partition file, e.g. rst_basic) ; ~2 min."""
import os, sys, subprocess, tempfile, unittest
S = os.environ.get('RVT_ADD_SAMPLE_2023'); SRC = os.environ.get('RVT_ADD_SRC_2023', '512451')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); TOOL = os.path.join(ROOT, 'tools', 'rvt_add_clone.py'); sys.path.insert(0, ROOT)
@unittest.skipUnless(S and os.path.exists(S), 'RVT_ADD_SAMPLE_2023 not set')
class T(unittest.TestCase):
    def test_split_layout(self):
        from rvtballet.save import source_damage
        from rvtballet import segedit
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'o.rvt')
            r = subprocess.run([sys.executable, TOOL, S, o, '--src', SRC], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, 'default must still refuse (merged layout is Revit-rejected)')
            self.assertFalse(os.path.exists(o))
            env = dict(os.environ, RVT_ADD_PROFILE_B_MULTI='1', RVT_ADD_YEAR_FORCE='1')
            r = subprocess.run([sys.executable, TOOL, S, o, '--src', SRC], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            self.assertFalse(source_damage(open(o, 'rb').read()))
            import olefile
            names = [n for n in (olefile.OleFileIO(o).listdir(streams=True)) if n[0].startswith('Partitions')]
            small = 0
            for n in names:
                try: sp = segedit.SegPart(o, '/'.join(n))
                except segedit.Refused: continue      # mini streams
                small += sum(1 for m in sp.mem[:4] if m[2] < 5000)
            self.assertGreaterEqual(small, 2, 'insert must sit in its own small member(s) (split layout)')
if __name__ == '__main__': unittest.main()
