"""c4x-rvtdiff 158: a template (.rte) edited into OUT.rvt was rejected by Revit ('not a valid .rvt file'); check_paths now refuses an extension change."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.editcli import check_paths
class T(unittest.TestCase):
    def test_mismatch_refused_same_ok(self):
        self.assertIn('extension', check_paths('/nonexistent/a.rte', '/nonexistent/b.rvt', False, False))
        self.assertIsNone(check_paths('/nonexistent/a.rte', '/nonexistent/b.rte', False, False))
        self.assertIsNone(check_paths('/nonexistent/a.RVT', '/nonexistent/b.rvt', False, False))
if __name__ == '__main__': unittest.main()
