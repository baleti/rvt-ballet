"""Revit-made move and rotate of a title block (house3 302064, category -2000280) commit but change NO element (c4x-rvtdiff witnesses tb_mv, tb_rot),
yet the writer saved a moved/rotated title block. Must be refused; doors still move. Fails without the category guard in edit-lab rvtedit.py."""
import os,subprocess,sys,tempfile,unittest
S=os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte'); E=os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
@unittest.skipUnless(os.path.exists(S) and os.path.exists(E),'lab files absent')
class T(unittest.TestCase):
    def run_(self,op,env=None):
        o=os.path.join(tempfile.mkdtemp(),'o.rte')
        p=subprocess.run([sys.executable,E,S,o,op],capture_output=True,text=True,cwd=os.path.dirname(E),env={**os.environ,**(env or {})})
        return p,os.path.exists(o)
    def test_refused(self):
        for op in ('mv:302064:1:0:0','rot:302064:30'):
            p,saved=self.run_(op); self.assertIn('title block 302064 refused',p.stderr); self.assertFalse(saved)
    def test_opt_in(self):
        p,saved=self.run_('mv:302064:1:0:0',{'RVTEDIT_MOVE_TITLEBLOCK':'1'}); self.assertTrue(saved,p.stderr[-200:])
    def test_door_still_moves(self):
        p,saved=self.run_('mv:301609:0.5:0:0'); self.assertTrue(saved,p.stderr[-200:])
if __name__=='__main__': unittest.main()
