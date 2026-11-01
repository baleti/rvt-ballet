"""verification worker: POSIX path unchanged (subprocess.run), Windows path goes through the Job Object launcher with the byte limit converted to GB and kills on timeout. Simulated platform."""
import os, sys, subprocess, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import save, plat

class T(unittest.TestCase):
    def test_posix(self):
        r = save._run_worker([sys.executable, '-c', 'print(3)'], 2 ** 31, 30); self.assertEqual((r.returncode, r.stdout.strip()), (0, '3'))
    def test_windows_job(self):
        got = {}
        class P:
            returncode = 0
            def communicate(self, timeout=None): return ('o', 'e')
        def fake(argv, gb, **kw): got['gb'] = gb; got['kw'] = kw; return P()
        with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(plat.proc, 'popen_capped', fake):
            r = save._run_worker(['x'], 4 * 2 ** 30, 5)
        self.assertEqual(got['gb'], 4.0); self.assertTrue(got['kw']['text']); self.assertEqual((r.stdout, r.stderr), ('o', 'e'))
    def test_windows_timeout_kills(self):
        killed = []
        class P:
            returncode = None
            def communicate(self, timeout=None):
                if timeout: raise subprocess.TimeoutExpired('x', timeout)
                return ('', '')
            def kill(self): killed.append(1)
        with mock.patch.object(sys, 'platform', 'win32'), mock.patch.object(plat.proc, 'popen_capped', lambda *a, **k: P()):
            with self.assertRaises(subprocess.TimeoutExpired): save._run_worker(['x'], 2 ** 30, 1)
        self.assertEqual(killed, [1])
if __name__ == '__main__': unittest.main()
