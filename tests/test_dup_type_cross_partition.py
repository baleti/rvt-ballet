"""Site 2024: symbol 131980 (partition 96) has its surrogate in partition 94; dup type must refuse with a clear message and write no output.
Needs the Snowdon Site 2024 sample; skipped when absent. A few minutes."""
import os, subprocess, sys, tempfile, unittest
S = os.path.expanduser('~/rvt-research/corpus/2024/47_Snowdon_Towers_Sample_Site.rvt')
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_dup_type_gen.py')
class X(unittest.TestCase):
    def test_refuse(self):
        if not os.path.exists(S): self.skipTest('no sample')
        with tempfile.TemporaryDirectory() as d:
            out = d + '/o.rvt'
            r = subprocess.run([sys.executable, T, S, out, '131980', 'C1XSITE'], capture_output=True, text=True, timeout=3000)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('different partitions', r.stdout + r.stderr)
            self.assertFalse(os.path.exists(out))
if __name__ == '__main__': unittest.main()
