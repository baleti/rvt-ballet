"""ADD must refuse a project whose persisted ElemTable counter is <= max element id (new id would collide).
Needs an Autodesk sample path in $RVT_ADD_SAMPLE (2024 single partition, e.g. HVAC) and $RVT_ADD_SRC (a childless-or-tolerated FamilyInstance id)."""
import os, sys, struct, subprocess, tempfile, unittest
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab'))
SAMPLE = os.environ.get('RVT_ADD_SAMPLE'); SRC = os.environ.get('RVT_ADD_SRC', '1365188')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')

@unittest.skipUnless(SAMPLE and os.path.exists(SAMPLE), 'RVT_ADD_SAMPLE not set')
class CounterGuard(unittest.TestCase):
    def test_refuses_low_counter(self):
        import rvtgen
        g = rvtgen.Gen(SAMPLE)
        def fn(raw):
            out = bytearray(raw); struct.pack_into('<I', out, len(out) - g.CTR, g.maxid - 5); return bytes(out)
        g.e.global_edit('Global/ElemTable', fn)
        with tempfile.TemporaryDirectory() as d:
            low = os.path.join(d, 'low.rvt'); g.e.save(low)
            r = subprocess.run([sys.executable, TOOL, low, os.path.join(d, 'o.rvt'), '--src', SRC], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('counter', r.stdout + r.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, 'o.rvt')))
if __name__ == '__main__': unittest.main()
