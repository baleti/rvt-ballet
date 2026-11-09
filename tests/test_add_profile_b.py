"""RVT_ADD_PROFILE=B must reproduce the Revit-2024-opened FI ADD layout (bis/B_nomerge, sha 50abe7a7ac6a7202) and pass the layout guard;
without the profile the single-partition default must keep its own layout. Needs $RVT_ADD_SAMPLE (Snowdon HVAC 2024, Autodesk sample)."""
import os, sys, subprocess, hashlib, tempfile, unittest
SAMPLE = os.environ.get('RVT_ADD_SAMPLE'); TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')
@unittest.skipUnless(SAMPLE and os.path.exists(SAMPLE), 'RVT_ADD_SAMPLE not set')
class T(unittest.TestCase):
    def test_profile_b_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'b.rvt')
            r = subprocess.run([sys.executable, TOOL, SAMPLE, out, '--src', '1365188'], capture_output=True, text=True, env=dict(os.environ, RVT_ADD_PROFILE='B'))
            self.assertEqual(r.returncode, 0, r.stderr[-300:])
            self.assertEqual(hashlib.sha256(open(out, 'rb').read()).hexdigest()[:16], '50abe7a7ac6a7202')
if __name__ == '__main__': unittest.main()
