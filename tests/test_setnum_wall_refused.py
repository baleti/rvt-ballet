"""A bare numeric parameter write on a wall (height -1001108) used to save a file whose height parameter said 15 ft while the
stored geometry (Envelope, GNode) still said 12 ft; Revit-made resize regenerates them (c4x-rvtdiff witness wiso2). Must be refused.
Fails without the guard in edit-lab rvtedit.py set_num."""
import os,subprocess,sys,tempfile,unittest
S=os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
E=os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
@unittest.skipUnless(os.path.exists(S) and os.path.exists(E),'lab files absent')
class T(unittest.TestCase):
    def run_(self,env=None):
        o=os.path.join(tempfile.mkdtemp(),'o.rte')
        p=subprocess.run([sys.executable,E,S,o,'dbl:301848:-1001108:15.0'],capture_output=True,text=True,env={**os.environ,**(env or {})})
        return p,os.path.exists(o)
    def test_refused(self):
        p,saved=self.run_(); self.assertIn('refused: its dimensions',p.stderr); self.assertFalse(saved)
    def test_opt_in(self):
        p,saved=self.run_({'RVTEDIT_SETNUM_GEOM':'1'}); self.assertTrue(saved,p.stderr[-200:])
    def test_floor_offset_refused(self):
        F=os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
        if not os.path.exists(F): self.skipTest('sample absent')
        o=os.path.join(tempfile.mkdtemp(),'f.rvt')
        p=subprocess.run([sys.executable,E,F,o,'dbl:621720:-1001955:1.5'],capture_output=True,text=True)
        self.assertIn('wall/floor 621720 refused',p.stderr); self.assertFalse(os.path.exists(o))
if __name__=='__main__': unittest.main()
