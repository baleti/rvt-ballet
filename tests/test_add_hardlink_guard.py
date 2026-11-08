"""SEVERITY 1 regression (c3x-rvtadd 2026-11-08): ADD with the output path hard-linked to the input overwrote the ORIGINAL in place (realpath differs, inode same).
rvt_add_clone must refuse and leave the input byte-identical. Fails without the guard (input hash changes)."""
import os, sys, shutil, hashlib, subprocess, tempfile, unittest
F = os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
h = lambda p: hashlib.sha1(open(p, 'rb').read()).hexdigest()

@unittest.skipUnless(os.path.exists(F), 'no corpus')
class Hardlink(unittest.TestCase):
    def test_hardlinked_output_refused_original_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            seed = os.path.join(d, 'seed.rvt'); out = os.path.join(d, 'out.rvt'); shutil.copy(F, seed); os.link(seed, out); before = h(seed)
            r = subprocess.run([sys.executable, TOOL, seed, out, '--src', '512451'], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('hard link', r.stdout + r.stderr); self.assertEqual(h(seed), before)
if __name__ == '__main__': unittest.main()
