"""rvt_join_cleanup refuses: unknown id (no output file), OUT == SRC (source bytes untouched)."""
import os, sys, hashlib, subprocess, tempfile, shutil, unittest
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_writer_mcls1.rte')
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
@unittest.skipUnless(os.path.exists(SRC), 'scene missing')
class T(unittest.TestCase):
    def run_tool(self, src, out, eid):
        return subprocess.run([sys.executable, R + '/tools/rvt_join_cleanup.py', src, out, eid], capture_output=True, text=True)
    def test_refusals(self):
        d = tempfile.mkdtemp(dir=os.path.expanduser('~/c3x-tmp-c4x'))
        try:
            before = sha(SRC); o = d + '/o.rte'
            self.assertNotEqual(self.run_tool(SRC, o, '999999').returncode, 0); self.assertFalse(os.path.exists(o))
            self.assertNotEqual(self.run_tool(SRC, SRC, '301593').returncode, 0)
            self.assertEqual(sha(SRC), before)
        finally: shutil.rmtree(d, ignore_errors=True)
if __name__ == '__main__': unittest.main()
