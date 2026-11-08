"""rvt_add_clone fails closed when the output splits the partition's first gzip member (layout Revit 2024 rejected with CorruptModelException twice).
HVAC 2024 sample + forced edit engine -> REFUSED, output removed. Needs $RVT_CORPUS (default ~/rvt-research/corpus); ~1.5 min."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_add_clone.py')

class LayoutGuard(unittest.TestCase):
    def test_split_first_member_refused(self):
        f = glob.glob(CORPUS + '/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
        if not f: self.skipTest('no corpus')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt')
            env = dict(os.environ, RVT_ADD_EDITENGINE='1', RVT_ADD_EDITENGINE_FORCE='1', HDR_SKIP='1', REC_SKIP='1', ITEM_SKIP='1')
            env.pop('RVT_ADD_LAYOUT_FORCE', None)
            r = subprocess.run([sys.executable, TOOL, f[0], out, '--src', '1365188'], capture_output=True, text=True, env=env)
            self.assertNotEqual(r.returncode, 0); self.assertIn('first member was split', r.stdout + r.stderr); self.assertFalse(os.path.exists(out))

    def test_single_partition_editengine_default_equals_writelab(self):
        """single-partition default for the edit engine is skip 0: output byte-identical to the write-lab engine (the build Revit 2024 opened clean). Fails with the old default skip 1 (split layout, refused)."""
        import hashlib
        f = glob.glob(CORPUS + '/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
        if not f: self.skipTest('no corpus')
        with tempfile.TemporaryDirectory() as d:
            h = []
            for k, extra in enumerate(({}, {'RVT_ADD_EDITENGINE': '1'})):
                out = os.path.join(d, 'o%d.rvt' % k); env = dict(os.environ, **extra)
                for _k in ('HDR_SKIP', 'REC_SKIP', 'ITEM_SKIP', 'RVT_ADD_LAYOUT_FORCE'): env.pop(_k, None)
                r = subprocess.run([sys.executable, TOOL, f[0], out, '--src', '1365188'], capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr); h.append(hashlib.sha1(open(out, 'rb').read()).hexdigest())
            self.assertEqual(h[0], h[1])
if __name__ == '__main__': unittest.main()
