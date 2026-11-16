"""c4x-rvtdiff 148: Revit-made delete of window 301612 (house3 2024, 4 nested generic models) cascades to 5 elements AND regenerates the host wall 301602 (WallCutoutGStep, face/edge history tables: witness ~/c2x-diff/c4x_asmdel). The writer cannot reproduce the wall regeneration, so the product must refuse (fail closed) and leave the file untouched."""
import os, subprocess, sys, tempfile, shutil, unittest
S = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
@unittest.skipUnless(os.path.exists(S), 'scene absent')
class T(unittest.TestCase):
    def test_refused(self):
        d = tempfile.mkdtemp(); shutil.copy(S, d + '/h.rvt'); o = d + '/o.rvt'
        p = subprocess.run([sys.executable, '-m', 'rvtballet', 'edit', d + '/h.rvt', '--delete', '301612', '-o', o], capture_output=True, text=True,
                           env={**os.environ, 'RVTBALLET_EDIT_BACKEND': 'rvtedit', 'RVTBALLET_ENABLE_DELETE': '1'}, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assertFalse(os.path.exists(o), p.stdout[-300:]); self.assertIn('refused', p.stdout + p.stderr)
        shutil.rmtree(d, ignore_errors=True)
if __name__ == '__main__': unittest.main()
