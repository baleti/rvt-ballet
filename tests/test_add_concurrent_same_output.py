"""Two rvt_add_clone runs to the SAME output path: they shared one fixed .part file (second run crashed on the rename, writes could interleave). .part names now carry the pid: both succeed, one valid output, no leftovers."""
import os, sys, glob, subprocess, tempfile, time, unittest
F = glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt'))
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(F, 'no corpus')
class Conc(unittest.TestCase):
    def test_two_runs(self):
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'o.rvt'); cmd = [sys.executable, TOOL, F[0], o, '--src', '1365188']
            p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True); time.sleep(2)
            p2 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            r = [p.communicate()[0] + str(p.returncode) for p in (p1, p2)]
            self.assertEqual([p1.returncode, p2.returncode], [0, 0], r); self.assertEqual(os.listdir(d), ['o.rvt'])
if __name__ == '__main__': unittest.main()
