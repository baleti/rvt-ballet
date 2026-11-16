"""c4x-rvtdiff 175: on 2026 files g.template has no header for the id, so the category lookup of the hosted-delete guard failed and a wall-hosted WINDOW (593207, Facades 2026, ledger PASS) was refused as 'hosted in a SWall'. The guard now falls back to the reader's header table (ElementHeader.m_categroryId)."""
import glob, os, subprocess, sys, unittest
F = glob.glob(os.path.expanduser('~/rvt-research/corpus/2026/*Facades*.rvt'))
@unittest.skipUnless(F, 'sample absent')
class T(unittest.TestCase):
    def test_not_refused_by_host_guard(self):
        code = ("import sys,os\n[sys.path.insert(0,os.path.expanduser(p)) for p in ('~/rvt-research/edit-lab','~/rvt-research/write-lab','~/rvt-research','%s')]\n"
                "os.environ.update(RVT_GEOM='1',RVTBALLET_EDIT_BACKEND='rvtedit',RVTBALLET_ENABLE_DELETE='1')\nimport rvtedit\nfrom rvtballet import edit\n"
                "ed=rvtedit.Edit(sys.argv[1]); ed._deleted_ids=[]\ntry: edit._delete(ed,593207); print('OK')\nexcept Exception as e: print('ERR',e)\n") % os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = subprocess.run([sys.executable, '-c', code, F[0]], capture_output=True, text=True)
        self.assertNotIn('hosted in a', p.stdout + p.stderr, p.stdout[-300:] + p.stderr[-300:])
if __name__ == '__main__': unittest.main()
