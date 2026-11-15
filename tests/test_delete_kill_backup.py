"""SIGKILL in the middle of the backup (.part half written) of an in-place delete SAVE!: the original must stay byte-identical, the half .part must not count as a backup, and a later normal save still works.
Needs $RVT_DEL_KILL_SAMPLE (Autodesk sample) and $RVT_DEL_KILL_EID."""
import os, sys, glob, signal, hashlib, tempfile, subprocess, unittest, fnmatch
S = os.environ.get('RVT_DEL_KILL_SAMPLE'); E = os.environ.get('RVT_DEL_KILL_EID')
WRAP = os.path.join(os.path.dirname(__file__), '..', 'tools', '_kill_in_backup.py')
def sha(p):
    with open(p, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()
def find(d, pat): return [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if fnmatch.fnmatch(f, pat)]
@unittest.skipUnless(S and E and os.path.exists(S), 'RVT_DEL_KILL_SAMPLE/EID not set')
class T(unittest.TestCase):
    def test_kill_in_backup(self):
        h0 = sha(S)
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, TMPDIR=d, DEL_EID=E)
            p = subprocess.run([sys.executable, WRAP, S], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3000)
            self.assertEqual(p.returncode, -signal.SIGKILL, 'hook never fired (rc=%s)' % p.returncode)
            fs = glob.glob(d + '/*/p.rvt'); self.assertTrue(fs, 'private copy missing')
            self.assertEqual(sha(fs[0]), h0, 'original changed by a kill during backup')
            parts = find(d, '*.part'); print('KILL_BACKUP parts_left=%d' % len(parts))
if __name__ == '__main__': unittest.main()
