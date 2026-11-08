"""IndependentTag ADD (edit-lab 'at' op) on the Autodesk 2024 HVAC sample: main reader must see exactly +1 IndependentTag, nothing gone or changed.
Offline only; needs ~/rvt-research/edit-lab and $RVT_CORPUS (default ~/rvt-research/corpus); skipped when absent. Revit verdicts are recorded separately."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

class AddTag(unittest.TestCase):
    def test_tag(self):
        f = glob.glob(CORPUS + '/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
        if not f or not os.path.exists(LAB): self.skipTest('no corpus/edit-lab')
        from rvtballet import reader
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 't.rvt')
            r = subprocess.run([sys.executable, LAB, f[0], out, 'at:1487400:1447768:1:1'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            a = reader.load(f[0])['recs']; b = reader.load(out)['recs']
            new = [k for k in b if k not in a]
            self.assertEqual([k[1] for k in new], ['IndependentTag'])
            self.assertFalse([k for k in a if k[0] and 'error' not in a[k] and k not in b])
            self.assertFalse([k for k in a if k in b and k[0] and 'error' not in a[k] and a[k] != b[k]])

if __name__ == '__main__': unittest.main()
