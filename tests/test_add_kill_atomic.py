"""SIGKILL of an ADD build mid-way never leaves a file at the requested output path (the build goes to a hidden .part file).
Needs $RVT_ADD_SAMPLE_2024 (Autodesk Snowdon HVAC 2024) and $RVT_ADD_SRC_2024 (e.g. 1365188)."""
import os, sys, subprocess, tempfile, unittest, time, signal
S = os.environ.get('RVT_ADD_SAMPLE_2024'); SRC = os.environ.get('RVT_ADD_SRC_2024', '1365188')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(S and os.path.exists(S), 'RVT_ADD_SAMPLE_2024 not set')
class T(unittest.TestCase):
    def test_kill_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'a.rvt')
            p = subprocess.Popen([sys.executable, TOOL, S, o, '--src', SRC], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(40); self.assertIsNone(p.poll(), 'build finished before the kill; sample too small for this test')
            p.send_signal(signal.SIGKILL); p.wait()
            self.assertFalse(os.path.exists(o))
    def test_sigterm_leaves_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            o = os.path.join(d, 'a.rvt')
            p = subprocess.Popen([sys.executable, TOOL, S, o, '--src', SRC], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(40); self.assertIsNone(p.poll(), 'build finished before the kill; sample too small for this test')
            p.send_signal(signal.SIGTERM); p.wait(timeout=60)
            self.assertEqual(os.listdir(d), [])
if __name__ == '__main__': unittest.main()
