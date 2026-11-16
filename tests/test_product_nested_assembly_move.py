"""c4x-rvtdiff 144: the PRODUCT path (rvt-ballet edit, savegate verify) accepts a move of a window with 4 nested sub-components (house3 synthetic scene, VM-verified lab move): the writer's extra members are declared as moves, gate reports 0 unexpected differences. Before the fix the gate refused with 2 differences outside the declared edit."""
import os, subprocess, sys, tempfile, shutil, unittest
S = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
@unittest.skipUnless(os.path.exists(S), 'scene absent')
class T(unittest.TestCase):
    def test_window_assembly_accepted_by_gate(self):
        d = tempfile.mkdtemp(); shutil.copy(S, d + '/h.rvt'); o = d + '/o.rvt'
        p = subprocess.run([sys.executable, '-m', 'rvtballet', 'edit', d + '/h.rvt', '--move', '301612', '0.5', '0', '0', '-o', o],
                           capture_output=True, text=True, env={**os.environ, 'RVTBALLET_EDIT_BACKEND': 'rvtedit'}, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assertTrue(os.path.exists(o), p.stdout[-300:] + p.stderr[-300:])
        self.assertIn('0 unexpected differences', p.stdout)
        shutil.rmtree(d, ignore_errors=True)
if __name__ == '__main__': unittest.main()
