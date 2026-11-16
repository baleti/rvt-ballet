"""--count 3 builds three consecutive ids, is deterministic (two builds byte-equal), and a count of 0/51 is refused with nothing written. Local-only corpus sample; skipped when absent."""
import hashlib, os, subprocess, sys, tempfile, unittest
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')
F = os.path.expanduser('~/rvt-research/corpus/2023/36_rst_basic_sample_project.rvt')
def run(*a, **k):
    e = dict(os.environ, RVT_ADD_PROFILE_B_MULTI='1')
    return subprocess.run([sys.executable, TOOL, *a], capture_output=True, text=True, timeout=1800, env=e)
class T(unittest.TestCase):
    def test_count3_deterministic(self):
        if not os.path.exists(F): self.skipTest('sample not present')
        with tempfile.TemporaryDirectory() as d:
            sh = []
            for n in 'ab':
                p = os.path.join(d, n + '.rvt'); r = run(F, p, '--src', '512451', '--count', '3')
                self.assertEqual(r.returncode, 0, r.stdout[-300:] + r.stderr[-300:]); self.assertIn('new id 1480132', r.stdout)
                sh.append(hashlib.sha256(open(p, 'rb').read()).hexdigest())
            self.assertEqual(sh[0], sh[1])
            for c in ('0', '51'):
                p = os.path.join(d, 'c' + c + '.rvt'); r = run(F, p, '--src', '512451', '--count', c)
                self.assertNotEqual(r.returncode, 0); self.assertFalse(os.path.exists(p))
if __name__ == '__main__': unittest.main()
