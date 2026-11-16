"""Revit-made move of nested sub-component 301619 (house3, Generic Model inside window 301612) moved the PARENT window and its 3 siblings
(c4x-rvtdiff witness gm_mv: 5 records, hostParam of the parent +0.5, Trf.m_or of the 4 children +0.5). The writer used to move 301619 alone.
Children and parents with nested children are refused; plain windows/doors still move. Fails without the guards in edit-lab rvtedit.py."""
import os,subprocess,sys,tempfile,unittest
S=os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte'); E=os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
@unittest.skipUnless(os.path.exists(S) and os.path.exists(E),'lab files absent')
class T(unittest.TestCase):
    def run_(self,op,env=None):
        o=os.path.join(tempfile.mkdtemp(),'o.rte')
        p=subprocess.run([sys.executable,E,S,o,op],capture_output=True,text=True,cwd=os.path.dirname(E),env={**os.environ,**(env or {})})
        return p,os.path.exists(o)
    def test_child_refused(self):
        for i in (301619,301622):
            p,saved=self.run_('mv:%d:0.5:0:0'%i); self.assertIn('nested in FamilyInstance 301612',p.stderr); self.assertFalse(saved)
    def test_parent_refused(self):
        p,saved=self.run_('mv:301612:0.5:0:0'); self.assertIn('nested sub-component',p.stderr); self.assertFalse(saved)
    def test_plain_still_moves(self):
        for i in (301609,301610):
            p,saved=self.run_('mv:%d:0.5:0:0'%i); self.assertTrue(saved,p.stderr[-200:])
if __name__=='__main__': unittest.main()
