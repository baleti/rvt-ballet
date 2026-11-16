"""c4x-rvtdiff 151 (severity 1, ESCAPE found 2026-11-16): delete of wall-hosted instances was accepted (window 593207 Facades 2024; narrowed 153: windows/doors in a straight wall are allowed again, VM Area/Volume equal; Generic Model 589763 Structural 2024 stays refused) with 'verified: 0 unexpected differences' although Revit regenerates 2 host walls and a dimension (witness ~/c2x-diff/c4x_wdel1). Must be refused, file untouched."""
import os, subprocess, sys, tempfile, shutil, unittest
S = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
@unittest.skipUnless(os.path.exists(S), 'scene absent')
class T(unittest.TestCase):
    def test_hosted_generic_model_refused_with_host_reason(self):
        d = tempfile.mkdtemp(); shutil.copy(S, d + '/h.rvt'); o = d + '/o.rvt'
        p = subprocess.run([sys.executable, '-m', 'rvtballet', 'edit', d + '/h.rvt', '--delete', '589763', '-o', o], capture_output=True, text=True,
                           env={**os.environ, 'RVTBALLET_EDIT_BACKEND': 'rvtedit', 'RVTBALLET_ENABLE_DELETE': '1'}, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assertFalse(os.path.exists(o)); self.assertIn('hosted in a', p.stdout + p.stderr)
        shutil.rmtree(d, ignore_errors=True)
if __name__ == '__main__': unittest.main()
