"""rvt_add_clone refuses a workshared (or unreadable-state) project before writing anything. Worksharing state is stubbed to 'Central' via a runpy wrapper
(no workshared Autodesk sample is on disk). Needs the 2020 rst_basic corpus file; fails without the guard (the tool builds the output)."""
import os, sys, subprocess, tempfile, unittest
F = os.path.expanduser('~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
WRAP = "import sys,runpy; sys.path.insert(0,%r); import rvtballet.save as s; s.worksharing_state=lambda b: %r; sys.argv=[%r]+sys.argv[1:]; runpy.run_path(%r, run_name='__main__')"

@unittest.skipUnless(os.path.exists(F), 'no corpus')
class Workshared(unittest.TestCase):
    def run_with(self, state):
        d = tempfile.mkdtemp(); out = os.path.join(d, 'o.rvt')
        code = WRAP % (os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), state, TOOL, TOOL)
        r = subprocess.run([sys.executable, '-c', code, F, out, '--src', '512451'], capture_output=True, text=True)
        return r, out
    def test_central_refused(self):
        r, out = self.run_with('Central'); self.assertNotEqual(r.returncode, 0); self.assertIn('Worksharing', r.stdout + r.stderr); self.assertFalse(os.path.exists(out))
    def test_unreadable_refused(self):
        r, out = self.run_with(None); self.assertNotEqual(r.returncode, 0); self.assertFalse(os.path.exists(out))
if __name__ == '__main__': unittest.main()
