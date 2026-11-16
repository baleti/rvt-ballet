"""BaseRailing 'Base Offset' 0 -> 0.5 on a Revit-made 2024 scene (rosetta railing): the Revit VM bounding box stayed unchanged after the edit (c4x-rvtmatrix 2026-11-16)
although the parameter read back 0.5, so a bare numeric write on a railing leaves stale geometry. Must be refused (RVTBALLET_SETNUM_GEOM=1 opts in). Fails without 'Railing' in rvtballet/edit.py _setnum_geom_class."""
import os, subprocess, tempfile, unittest
F = os.path.expanduser('~/rvt-research/rosetta/2024_railing_base.rte')
@unittest.skipUnless(os.path.exists(F), 'scene absent')
class T(unittest.TestCase):
    def test_refused(self):
        o = os.path.join(tempfile.mkdtemp(), 'o.rte')
        p = subprocess.run(['rvt-ballet', 'edit', F, '--set-num', '301555', 'Base Offset', '0.5', '-o', o], capture_output=True, text=True, env={**os.environ, 'RVTBALLET_EDIT_BACKEND': 'rvtedit'})
        self.assertFalse(os.path.exists(o), p.stdout[-300:]); self.assertIn('drive stored geometry', p.stdout + p.stderr)
if __name__ == '__main__': unittest.main()
