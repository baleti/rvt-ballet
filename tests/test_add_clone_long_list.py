"""ADD (rvt_add_clone) of a FamilyInstance that sits deep (index 800) in the 942-id Global/Latest list must register the new id in EVERY list holding the source (942 and 1191 ids). rvt_idlist.find_lists scanned only 64 entries back: refused (src 'in no list') or, when a short list also held it, registered the id in some lists only. Autodesk sample."""
import os, sys, re, struct, subprocess, tempfile, unittest
for p in ('~/rvt-research/write-lab', '~/rvt-research/edit-lab', '~/rvt-research'): sys.path.insert(0, os.path.expanduser(p))
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(os.path.exists(F), 'no corpus')
class Deep(unittest.TestCase):
    def test_both_lists(self):
        import adiff
        a = adiff.graw(F, 'Global/Latest'); src = struct.unpack_from('<Q', a, 153703 + 4 + 8 * 800)[0]
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'o.rvt'); r = subprocess.run([sys.executable, TOOL, '--src', str(src), '--dx', '1', F, o], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn('latest lists [942, 1191]', r.stdout)
            b = adiff.graw(o, 'Global/Latest'); nid = int(re.search(r'new id (\d+)', r.stdout).group(1))
            self.assertEqual(len(re.findall(re.escape(struct.pack('<Q', nid)), b)), 2)
            self.assertEqual(struct.unpack_from('<I', b, 153703)[0], 943)
if __name__ == '__main__': unittest.main()
