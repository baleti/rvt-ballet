"""SEV-1 regression (c2x-rvtmatrix, 2026-11-13): the savegate element/layout verify ACCEPTS the legacy edit-lab tag ADD default-layout output on the
Autodesk Structural 2024 sample, which Revit 2024 refuses to open (CArchiveException 105, offline VM verdict c2xtag85). Expected: the gate REFUSES it.
Gate layout rule now present (unexpected success seen 2026-11-15, marker removed). Needs corpus + edit-lab + savegate; ~4 min; set RVT_SLOW=1 to run."""
import os, sys, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
SRC = CORPUS + '/2024/43_Snowdon_Towers_Sample_Structural.rvt'

class TagAddLayoutEscape(unittest.TestCase):
    def test_default_layout_must_be_refused(self):
        if os.environ.get('RVT_SLOW') != '1' or not os.path.exists(SRC) or not os.path.exists(LAB): self.skipTest('set RVT_SLOW=1 and provide corpus + edit-lab')
        sys.path.insert(0, os.path.expanduser('~/src/savegate'))
        try:
            import savegate as sg
            from savegate import core, rvt_elements
            from savegate.adapters import RvtAdapter
        except ImportError: self.skipTest('no savegate')
        with tempfile.TemporaryDirectory(dir=os.path.expanduser(os.environ.get('RVT_TMPDIR', '~'))) as d:
            os.environ['SAVEGATE_JOURNAL'] = d + '/j'; os.environ['SAVEGATE_CACHE'] = d + '/c'
            out = d + '/t.rvt'; env = dict(os.environ); env.pop('RVTGEN_INPLACE', None)
            r = subprocess.run([sys.executable, LAB, SRC, out, 'at:871862:687059:1:1'], capture_output=True, text=True, cwd=os.path.dirname(LAB), env=env)
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            cfg = sg.Config(allow_overwrite=True, require_gate=False, journal_dir=d + '/j')
            doc = core.open_doc(SRC, RvtAdapter(elements_fn=rvt_elements.elements), cfg=cfg, journal=False)
            nb = open(out, 'rb').read(); a, b = doc.adapter.snapshot(doc.buf), doc.adapter.snapshot(nb)
            new = [k for k in b if k not in a]
            with self.assertRaises(Exception): core._verify(doc, nb, {'added': new})
if __name__ == '__main__': unittest.main()
