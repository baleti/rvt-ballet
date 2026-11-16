"""savegate verify of a --count 2 ADD (HVAC 2024): both new ids declared ACCEPTED; only 1 declared REFUSED; empty manifest REFUSED. Local corpus + savegate; skipped when absent."""
import os, sys, subprocess, tempfile, unittest
F = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
class T(unittest.TestCase):
    def test_multi_declared(self):
        if not os.path.exists(F): self.skipTest('sample not present')
        try:
            sys.path.insert(0, os.path.expanduser('~/src/savegate')); import savegate as sg
            from savegate import core, rvt_elements
            from savegate.adapters import RvtAdapter
        except ImportError: self.skipTest('no savegate')
        with tempfile.TemporaryDirectory() as d:
            os.environ['SAVEGATE_JOURNAL'] = d + '/j'; os.environ['SAVEGATE_CACHE'] = d + '/c'
            out = os.path.join(d, 'm.rvt')
            r = subprocess.run([sys.executable, TOOL, F, out, '--src', '1377544', '--count', '2'], capture_output=True, text=True, timeout=1800, env=dict(os.environ, RVT_ADD_PROFILE_B_MULTI='1'))
            self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:])
            cfg = sg.Config(allow_overwrite=True, require_gate=False, journal_dir=d + '/j')
            doc = core.open_doc(F, RvtAdapter(elements_fn=rvt_elements.elements), cfg=cfg, journal=False)
            nb = open(out, 'rb').read(); a, b = doc.adapter.snapshot(doc.buf), doc.adapter.snapshot(nb)
            new = sorted(k for k in b if k not in a); self.assertEqual(len(new), 2, new)
            for m in ({}, {'added': new[:1]}):
                with self.assertRaises(Exception): core._verify(doc, nb, m)
            core._verify(doc, nb, {'added': new})
if __name__ == '__main__': unittest.main()
