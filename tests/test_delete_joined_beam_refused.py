"""Deleting a joined beam (synthetic write-lab mcls1 2024, beams 301593/301597) is refused and writes nothing: Revit's own delete regenerates the partners' geometry symbols
(c4x-rvtdiff 291a), a record-only delete is not equivalent."""
import os, sys, subprocess, tempfile, shutil, hashlib, unittest
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_writer_mcls1.rte')
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
@unittest.skipUnless(os.path.exists(SRC), 'scene missing')
class T(unittest.TestCase):
    def test_refused(self):
        d = tempfile.mkdtemp(dir=os.path.expanduser('~/c3x-tmp-c4x')); b = hashlib.sha256(open(SRC, 'rb').read()).hexdigest()
        try:
            for eid in ('301593', '301597'):
                o = os.path.join(d, 'o%s.rte' % eid)
                p = subprocess.run([R + '/bin/rvt-ballet', 'edit', SRC, '-o', o, '--delete', eid], capture_output=True, text=True, env=dict(os.environ, RVTBALLET_ENABLE_DELETE='1'))
                self.assertIn('joined', p.stdout + p.stderr); self.assertFalse(os.path.exists(o), eid)
            self.assertEqual(hashlib.sha256(open(SRC, 'rb').read()).hexdigest(), b)
        finally: shutil.rmtree(d, ignore_errors=True)
if __name__ == '__main__': unittest.main()
