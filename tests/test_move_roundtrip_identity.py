"""c4x-rvtdiff 162: move +0.5 ft then -0.5 ft of window 301610 in two SEPARATE saves returns the decompressed partition body to the original (0 differing byte runs, 0 changed elements; product chain measured 2026-11-16 house3 2024). Pins that the writer leaves no residue (no drift in checksums, lengths, zone copies) across generations."""
import os, subprocess, sys, tempfile, unittest, re
S = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte'); E = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_diff.py')
@unittest.skipUnless(os.path.exists(S) and os.path.exists(E), 'lab files absent')
class X(unittest.TestCase):
    def test_there_and_back(self):
        d = tempfile.mkdtemp(); a, b = d + '/a.rte', d + '/b.rte'
        for src, dst, op in ((S, a, 'mv:301610:0.5:0:0'), (a, b, 'mv:301610:-0.5:0:0')):
            p = subprocess.run([sys.executable, E, src, dst, op], capture_output=True, text=True, cwd=os.path.dirname(E)); self.assertTrue(os.path.exists(dst), p.stderr[-300:])
        r = subprocess.run([sys.executable, T, S, b, '--max', '5'], capture_output=True, text=True).stdout
        self.assertRegex(r, r'0 differing byte runs'); self.assertRegex(r, r'changed 0 ')
if __name__ == '__main__': unittest.main()
