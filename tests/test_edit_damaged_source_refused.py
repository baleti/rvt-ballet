"""c4x-rvtdiff 170-172: a damaged source (bit flip in the main partition stream, a flip in the Contents stream, a truncated file) must be refused by the product edit, nothing written. Measured 2026-11-16 on the synthetic house3 2024 scene: 15 of 15 damaged copies refused."""
import os, subprocess, sys, tempfile, unittest, shutil
S = os.path.expanduser('~/rvt-research/write-lab/scenes/2024_house3.rte')
@unittest.skipUnless(os.path.exists(S), 'scene absent')
class T(unittest.TestCase):
    def _run(self, data):
        d = tempfile.mkdtemp(); f = d + '/f.rte'; o = d + '/o.rte'; open(f, 'wb').write(data)
        p = subprocess.run([sys.executable, '-m', 'rvtballet', 'edit', f, '--move', '301610', '0.5', '0', '0', '-o', o], capture_output=True, text=True,
                           env={**os.environ, 'RVTBALLET_EDIT_BACKEND': 'rvtedit'}, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ok = os.path.exists(o); shutil.rmtree(d, ignore_errors=True); return ok, p.stdout + p.stderr
    def test_cases(self):
        raw = open(S, 'rb').read()
        for name, mk in (('partition flip', lambda b: (b.__setitem__(3359578, b[3359578] ^ 0x40), b)[1]), ('Contents flip', lambda b: (b.__setitem__(22221, b[22221] ^ 0x01), b)[1]), ('truncated', lambda b: b[:len(b) - 1048576])):
            ok, out = self._run(bytes(mk(bytearray(raw)))); self.assertFalse(ok, name + ': ' + out[-300:])
if __name__ == '__main__': unittest.main()
