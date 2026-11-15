"""Revit-made rotate of a wall-hosted door (house3 301609, 30 deg) committed but changed no element
(c4x-rvtdiff door_rot witness), so the writer must refuse instead of saving a state Revit never makes.
Fails without the guard in edit-lab rvtedit.py (rotate would save)."""
import os,subprocess,sys,tempfile,unittest
S=os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
E=os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
@unittest.skipUnless(os.path.exists(S) and os.path.exists(E),'lab files absent')
class T(unittest.TestCase):
    def run_(self,env=None):
        d=tempfile.mkdtemp(); o=os.path.join(d,'o.rte')
        p=subprocess.run([sys.executable,E,S,o,'rot:301609:30'],capture_output=True,text=True,env={**os.environ,**(env or {})})
        return p,os.path.exists(o)
    def test_refused(self):
        p,saved=self.run_()
        self.assertIn('rotate of wall-hosted instance',p.stderr); self.assertFalse(saved)
    def test_opt_in_saves(self):
        p,saved=self.run_({'RVTEDIT_ROTATE_HOSTED':'1'}); self.assertTrue(saved,p.stderr[-300:])
if __name__=='__main__': unittest.main()
