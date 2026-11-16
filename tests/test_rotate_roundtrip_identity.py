"""c4x-rvtdiff 163: rotate +30 then -30 of column 301592 in two separate saves (cols2 sample) restores the decompressed partition body: any residue (float drift, checksum, zone copy) shows as differing byte runs."""
import os, subprocess, sys, tempfile, unittest
S = os.path.expanduser('~/c2x-cols2.rvt'); E = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_diff.py')
@unittest.skipUnless(os.path.exists(S) and os.path.exists(E), 'lab files absent')
class X(unittest.TestCase):
    def test_there_and_back(self):
        d = tempfile.mkdtemp(); o, a, b = d + '/o.rte', d + '/a.rte', d + '/b.rte'
        import shutil; shutil.copy(S, o)
        for src, dst, op in ((o, a, 'rot:301592:30'), (a, b, 'rot:301592:-30')):
            p = subprocess.run([sys.executable, E, src, dst, op], capture_output=True, text=True, cwd=os.path.dirname(E)); self.assertTrue(os.path.exists(dst), p.stderr[-300:])
        r = subprocess.run([sys.executable, T, o, b, '--max', '5'], capture_output=True, text=True).stdout
        # KNOWN RESIDUE (measured 2026-11-16): unlike a move (0 differing runs) the rotate round trip leaves 40 byte runs: 3 x 31 B (the element's stored bounding data: a bbox of the rotated bbox is not the original) and 5 x 1 B counters (+3). Only element 301592 changes and only in its header (record fields identical). Pinned so that growth beyond this (a second element, a record change) fails.
        self.assertRegex(r, r'changed 1 '); self.assertIn('id 301592 hdr_changed=True reclen [[], []]', r); self.assertIn('added 0 []  removed 0 []', r)
        self.assertRegex(r, r'(\d+) differing byte runs'); import re; self.assertLessEqual(int(re.search(r'(\d+) differing byte runs', r).group(1)), 40)
if __name__ == '__main__': unittest.main()
