"""Product path (rvt-ballet edit --set-num) on a Floor: 'Height Offset From Level' 0 -> 1.5 used to be accepted and saved a file whose Revit readback said
offset 1.5 but Elevation at Bottom/Top stayed 5.0/5.5 (Revit VM elemhash, c4x-rvtdiff 2026-11-16; a Revit-made change gives 6.5/7.0). Must be refused;
RVTBALLET_SETNUM_GEOM=1 opts in. Fails without the guard in rvtballet/edit.py _set_num_by_pid."""
import os,subprocess,sys,tempfile,unittest
F=os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
@unittest.skipUnless(os.path.exists(F),'sample absent')
class T(unittest.TestCase):
    def run_(self,env=None):
        o=os.path.join(tempfile.mkdtemp(),'o.rvt')
        p=subprocess.run(['rvt-ballet','edit',F,'--set-num','621720','Height Offset From Level','1.5','-o',o],capture_output=True,text=True,env={**os.environ,'RVTBALLET_EDIT_BACKEND':'rvtedit',**(env or {})})
        return p,os.path.exists(o)
    def test_refused(self):
        p,saved=self.run_(); self.assertFalse(saved,p.stdout[-300:]); self.assertIn('floor or wall',p.stdout+p.stderr)
    def test_wall_refused(self):
        """Structural 2024 wall 585072 Top Offset 0 -> 2: Revit readback Unconnected Height 78.75 but Area 780.29 / Volume 645.19 unchanged (stale geometry)"""
        o=os.path.join(tempfile.mkdtemp(),'w.rvt')
        p=subprocess.run(['rvt-ballet','edit',F,'--set-num','585072','Top Offset','2.0','-o',o],capture_output=True,text=True,env={**os.environ,'RVTBALLET_EDIT_BACKEND':'rvtedit'})
        self.assertFalse(os.path.exists(o),p.stdout[-300:]); self.assertIn('floor or wall',p.stdout+p.stderr)
if __name__=='__main__': unittest.main()
