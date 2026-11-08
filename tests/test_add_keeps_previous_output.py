"""A refused ADD must not destroy a pre-existing output file (c3x-rvtadd 2026-11-08: the layout guard removed the user's earlier output). Needs the 2023 Arch_Link_Model corpus file (default engine REFUSED by the layout guard)
and the 2020 rst_basic file (success path leaves no .part file)."""
import os, sys, subprocess, tempfile, unittest, glob
C = os.path.expanduser('~/rvt-research/corpus')
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')

class Keep(unittest.TestCase):
    def test_refused_build_keeps_previous_output(self):
        f = C + '/2023/38_Arch_Link_Model.rvt'
        if not os.path.exists(f): self.skipTest('no corpus')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt'); open(out, 'wb').write(b'previous good output')
            r = subprocess.run([sys.executable, TOOL, f, out, '--src', '172320'], capture_output=True, text=True, env=dict(os.environ, RVT_ADD_EDITENGINE='1'))
            self.assertNotEqual(r.returncode, 0); self.assertIn('REFUSED', r.stdout + r.stderr)
            self.assertEqual(open(out, 'rb').read(), b'previous good output'); self.assertEqual(os.listdir(d), ['o.rvt'])
    def test_success_leaves_no_part_file(self):
        f = C + '/2020/18_rst_basic_sample_project.rvt'
        if not os.path.exists(f): self.skipTest('no corpus')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt')
            r = subprocess.run([sys.executable, TOOL, f, out, '--src', '512451'], capture_output=True, text=True); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(sorted(os.listdir(d)), ['o.rvt']); self.assertGreater(os.path.getsize(out), 1000000)
    def test_write_failure_keeps_previous_output(self):
        """disk-full stand-in: RLIMIT_FSIZE makes the write fail with EFBIG; previous output intact, no .part left."""
        import resource, signal
        f = C + '/2020/18_rst_basic_sample_project.rvt'
        if not os.path.exists(f): self.skipTest('no corpus')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt'); open(out, 'wb').write(b'previous good output')
            def lim():
                signal.signal(signal.SIGXFSZ, signal.SIG_IGN); resource.setrlimit(resource.RLIMIT_FSIZE, (4 << 20, 4 << 20))
            r = subprocess.run([sys.executable, TOOL, f, out, '--src', '512451'], capture_output=True, text=True, preexec_fn=lim)
            self.assertNotEqual(r.returncode, 0); self.assertEqual(open(out, 'rb').read(), b'previous good output'); self.assertEqual(os.listdir(d), ['o.rvt'])
if __name__ == '__main__': unittest.main()
