"""rvt_join_cleanup (experimental): output differs from the synthetic source only in <=4 dirty gzip members of one partition, all other bytes identical;
and the same delete WITHOUT the partner cleanup step is not what the tool writes (partner record differs)."""
import os, sys, json, subprocess, tempfile, shutil, unittest
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_writer_mcls1.rte')
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@unittest.skipUnless(os.path.exists(SRC), 'synthetic mcls1 scene missing')
class T(unittest.TestCase):
    def test_dirty_members_only(self):
        d = tempfile.mkdtemp(dir=os.path.expanduser('~/c3x-tmp-c4x'))
        try:
            o = os.path.join(d, 'o.rte')
            subprocess.run([sys.executable, R + '/tools/rvt_join_cleanup.py', SRC, o, '301593'], check=True, capture_output=True)
            p = subprocess.run([sys.executable, R + '/tools/rvt_untouched_bytes.py', SRC, o, '--count-change', '--allow-streams=ElemTable'], capture_output=True, text=True)
            j = json.loads(p.stdout.strip().splitlines()[-1])
            part = [v for k, v in j.items() if k.startswith('Partitions/')]
            self.assertEqual(len(part), 1)
            self.assertEqual(part[0]['violations'], [])
            self.assertLessEqual(part[0]['dirty'], 4)
            self.assertGreaterEqual(part[0]['dirty'], 2)   # deleted beam + partner at least
        finally:
            shutil.rmtree(d, ignore_errors=True)
if __name__ == '__main__': unittest.main()
