"""No-op save through the lab writer (Autodesk Construction-DefaultMetric.rte 2024): same stream set, 0 changed elements, and EVERY page of every
Partitions/* stream has a valid ECC trailer (the last partial page may differ from the source in its spare bits/parity; c4x-rvtdiff 2026-11-15,
VM-verified for HVAC 2024/2025/2026). Breaks if the writer ever emits a page with a wrong trailer (Revit dies on those, write-lab LOG M2)."""
import os,subprocess,sys,tempfile,unittest
CORPUS=os.environ.get('RVT_CORPUS',os.path.expanduser('~/rvt-research/corpus'))
SRC=os.path.join(CORPUS,'2024','71_Construction-DefaultMetric.rte')
LAB=os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py'); ECC=os.path.expanduser('~/rvt-research/write-lab')
@unittest.skipUnless(os.path.exists(SRC) and os.path.exists(LAB),'sample/lab absent')
class T(unittest.TestCase):
    def test_noop(self):
        import olefile; sys.path.insert(0,ECC); import ecc
        sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','tools')); import rvt_diff
        out=os.path.join(tempfile.mkdtemp(),'o.rte')
        r=subprocess.run([sys.executable,LAB,SRC,out],capture_output=True,text=True,cwd=os.path.dirname(LAB)); self.assertTrue(os.path.exists(out),r.stderr[-300:])
        a,b=olefile.OleFileIO(SRC),olefile.OleFileIO(out); self.assertEqual(sorted(a.listdir()),sorted(b.listdir()))
        bad=0
        for s in b.listdir():
            if s[0]!='Partitions': continue
            x=b.openstream(s).read()
            for k in range(0,len(x),65249):
                if len(x[k:k+65249])>=400 and not ecc.check(x[k:k+65249]): bad+=1
        self.assertEqual(bad,0)
        rep=rvt_diff.diff(SRC,out,True,50,[]); self.assertEqual(len(rep['changed']),0); self.assertEqual((rep['n_added'],rep['n_removed']),(0,0))
if __name__=='__main__': unittest.main()
