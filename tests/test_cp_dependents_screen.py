"""edit-lab 'cp' op must refuse a source instance that owns dependents (ElementGroup etc.): no output file, rc != 0.
Needs the Autodesk 2022 Arch_Link_Model sample under $RVT_CORPUS (default ~/rvt-research/corpus); skipped when absent."""
import os, sys, glob, subprocess, tempfile, unittest
CORPUS = os.environ.get('RVT_CORPUS', os.path.expanduser('~/rvt-research/corpus'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')

class CpScreen(unittest.TestCase):
    def test_group_owner_refused(self):
        f = glob.glob(CORPUS + '/2022/*Arch_Link*.rvt')
        if not f or not os.path.exists(LAB): self.skipTest('no corpus/edit-lab')
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'o.rvt')
            env = {k: v for k, v in os.environ.items() if k != 'RVTEDIT_COPY_FORCE'}
            r = subprocess.run([sys.executable, LAB, f[0], out, 'cp:170566:1:1'], capture_output=True, text=True, cwd=os.path.dirname(LAB), env=env)
            self.assertNotEqual(r.returncode, 0, (r.stdout + r.stderr)[-300:])
            self.assertFalse(os.path.exists(out))
if __name__ == '__main__': unittest.main()
