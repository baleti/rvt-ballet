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
            p,saved=self.run_('mv:%d:0.5:0:0'%i); self.assertIn('nested assembly (parent 301612',p.stderr); self.assertFalse(saved)
    def test_parent_refused(self):
        p,saved=self.run_('mv:301612:0.5:0:0'); self.assertIn('nested assembly',p.stderr); self.assertFalse(saved)
    def test_plain_still_moves(self):
        for i in (301609,301610):
            p,saved=self.run_('mv:%d:0.5:0:0'%i); self.assertTrue(saved,p.stderr[-200:])
    def test_column_in_chain_still_moves(self):
        """the id before a column's own id in its header can be the previous column in a list (301563), not an owner: false positive of the first guard version"""
        C=os.path.expanduser('~/c3x-tmp-c4x/kp/2024_writer_cols2_Bool.rte')
        if not os.path.exists(C): self.skipTest('cols2 scene absent')
        o=os.path.join(tempfile.mkdtemp(),'c.rte')
        p=subprocess.run([sys.executable,E,C,o,'mv:301592:0.5:0:0'],capture_output=True,text=True,cwd=os.path.dirname(E))
        self.assertTrue(os.path.exists(o),p.stderr[-200:])
    def test_joined_real_column_still_moves(self):
        """Snowdon Structural 2024 column 606069 (joined to 4 elements; its header id list names beam 606875) has many Revit-verified moves: joins are not nesting"""
        F=os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
        if not os.path.exists(F): self.skipTest('sample absent')
        o=os.path.join(tempfile.mkdtemp(),'c.rvt')
        p=subprocess.run([sys.executable,E,F,o,'mv:606069:1:0:0'],capture_output=True,text=True,cwd=os.path.dirname(E))
        self.assertTrue(os.path.exists(o),p.stderr[-200:])
    def test_rotate_parent_refused_and_column_rotates(self):
        F=os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
        if not os.path.exists(F): self.skipTest('sample absent')
        d=tempfile.mkdtemp(); o=os.path.join(d,'p.rvt')
        p=subprocess.run([sys.executable,E,F,o,'rot:642543:30'],capture_output=True,text=True,cwd=os.path.dirname(E))
        self.assertIn('nested sub-component',p.stderr); self.assertFalse(os.path.exists(o))
        o2=os.path.join(d,'c.rvt')
        p=subprocess.run([sys.executable,E,F,o2,'rot:606069:30'],capture_output=True,text=True,cwd=os.path.dirname(E))
        self.assertTrue(os.path.exists(o2),p.stderr[-200:])
    def test_opt_in_assembly_equals_revit(self):
        """RVTEDIT_MOVE_NESTED=1: parent (hostParam+Trf) and all 4 children (Trf only) move together; offline record diff equals the Revit-made move (gm_mv witness, ~/c2x-diff/gm_mv/BASE_AFTER.json). Not VM-verified, so default stays refusal."""
        R=os.path.expanduser('~/c2x-diff/gm_mv/BASE_AFTER.json')
        if not os.path.exists(R): self.skipTest('Revit-made witness json absent')
        d=tempfile.mkdtemp(); o=os.path.join(d,'n.rte'); j=os.path.join(d,'n.json')
        p,saved=self.run_('mv:301619:0.5:0:0',{'RVTEDIT_MOVE_NESTED':'1'}) if False else (None,None)
        pr=subprocess.run([sys.executable,E,S,o,'mv:301619:0.5:0:0'],capture_output=True,text=True,cwd=os.path.dirname(E),env={**os.environ,'RVTEDIT_MOVE_NESTED':'1'})
        self.assertTrue(os.path.exists(o),pr.stderr[-200:])
        T=os.path.join(os.path.dirname(__file__),'..','tools')
        subprocess.run([sys.executable,os.path.join(T,'rvt_diff.py'),S,o,'--json',j],capture_output=True)
        c=subprocess.run([sys.executable,os.path.join(T,'rvt_diff_cmp.py'),R,j],capture_output=True,text=True)
        bad=[l for l in c.stdout.splitlines() if l.startswith('id ')]
        self.assertEqual(bad,[],bad[:5])
if __name__=='__main__': unittest.main()
