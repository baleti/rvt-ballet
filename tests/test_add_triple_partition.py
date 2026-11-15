"""The ElemTable row triple of an ADD comes from the max row of the BUILD partition (edc71ee). Single-partition builds must stay byte-identical to the files Revit opened (VM 2026-11-08/14).
Local-only corpus samples; skipped when absent."""
import hashlib, os, subprocess, sys, tempfile, unittest
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py')
C = os.path.expanduser('~/rvt-research/corpus')
CASES = [  # (sample, src, env, sha256 of the Revit-opened output)
    ('2024/42_Snowdon_Towers_Sample_HVAC.rvt', '1365188', {}, '50abe7a7ac6a7202'),
    ('2025/48_Snowdon_Towers_Sample_HVAC.rvt', '1365188', {'RVT_ADD_YEAR_FORCE': '1', 'RVT_ADD_PROFILE_B_MULTI': '1'}, 'd4d1c169b68e3c67'),      # 2 non-empty partitions, built in the last one: Revit PASS (pb25); guard must admit it
    ('2023/36_rst_basic_sample_project.rvt', '512451', {'RVT_ADD_PROFILE_B_MULTI': '1'}, '307cfdd12c30051a'),
]
class T(unittest.TestCase):
    def test_pass_builds_unchanged(self):
        ran = 0
        for rel, src, env, sha in CASES:
            f = os.path.join(C, rel)
            if not os.path.exists(f): continue
            with tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, 'o.rvt'); e = dict(os.environ, **env)
                r = subprocess.run([sys.executable, TOOL, f, out, '--src', src], capture_output=True, text=True, timeout=1800, env=e)
                self.assertEqual(r.returncode, 0, r.stdout[-400:] + r.stderr[-400:])
                self.assertTrue(hashlib.sha256(open(out, 'rb').read()).hexdigest().startswith(sha), rel); ran += 1
        if not ran: self.skipTest('samples not present')
if __name__ == '__main__': unittest.main()
