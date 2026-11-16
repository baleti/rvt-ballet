"""c4x-rvtdiff 167: query collect --fields Mark returned blank for a Mark stored as ParamValueAString (house3 2024 window 301610 = 'W1.0.1'); fails without the BUILTIN_PARAM_FIELDS lookup."""
import os, shutil, subprocess, sys, tempfile, unittest
S = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
@unittest.skipUnless(os.path.exists(S), 'scene absent')
class T(unittest.TestCase):
    def test_mark(self):
        d = tempfile.mkdtemp(); shutil.copy(S, d + '/h.rvt')
        p = subprocess.run([sys.executable, '-m', 'rvtballet', 'query', 'collect', d + '/h.rvt', '--class', 'FamilyInstance', '--fields', 'Mark', '--where', 'id=301610', '--tsv'], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assertIn('W1.0.1', p.stdout, p.stdout + p.stderr[-300:]); shutil.rmtree(d, ignore_errors=True)
if __name__ == '__main__': unittest.main()
