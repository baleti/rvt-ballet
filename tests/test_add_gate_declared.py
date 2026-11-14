"""savegate element-level verify of a tag ADD: empty manifest REFUSED, wrong declared id REFUSED, correct 'added' id ACCEPTED.
Needs HVAC 2024 sample + edit-lab (built into a temp dir); skipped when absent. ~2 min."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

class GateDeclared(unittest.TestCase):
    def test_declared_add(self):
        f = glob.glob(CORPUS + '/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
        if not f or not os.path.exists(LAB): self.skipTest('no corpus/edit-lab')
        try:
            sys.path.insert(0, os.path.expanduser('~/src/savegate')); import savegate as sg
            from savegate import core, rvt_elements
            from savegate.adapters import RvtAdapter
        except ImportError: self.skipTest('no savegate')
        with tempfile.TemporaryDirectory() as d:
            os.environ['SAVEGATE_JOURNAL'] = d + '/j'; os.environ['SAVEGATE_CACHE'] = d + '/c'
            out = os.path.join(d, 't.rvt')
            r = subprocess.run([sys.executable, LAB, f[0], out, 'at:1487400:1447768:1:1'], capture_output=True, text=True, cwd=os.path.dirname(LAB))
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            cfg = sg.Config(allow_overwrite=True, require_gate=False, journal_dir=d + '/j')
            doc = core.open_doc(f[0], RvtAdapter(elements_fn=rvt_elements.elements), cfg=cfg, journal=False)
            nb = open(out, 'rb').read()
            a, b = doc.adapter.snapshot(doc.buf), doc.adapter.snapshot(nb)
            new = [k for k in b if k not in a]; self.assertEqual(len(new), 1)
            for m in ({}, {'added': ['el:1']}):
                with self.assertRaises(Exception): core._verify(doc, nb, m)
            core._verify(doc, nb, {'added': new, 'modified': ['el:1447768']})      # the tagged element's own record also changes (record_identity: every changed record must be declared); an 'added'-only manifest is refused since the record_identity rule
if __name__ == '__main__': unittest.main()
