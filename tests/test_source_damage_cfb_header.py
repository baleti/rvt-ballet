"""c7x-rvtread 94: a CFB major-version byte flip is loaded by the reader but refused by Revit 2024 (VM, COleException 0x80030105); the save gate must flag it."""
import os, sys, glob, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import save
S = (glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/69_*.rte')) or [None])[0]
@unittest.skipUnless(S, 'sample corpus absent')
class T(unittest.TestCase):
    def test_clean_not_flagged(self):
        self.assertEqual(save.source_damage(open(S, 'rb').read()), [])
    def test_major_version_flip_flagged(self):
        b = bytearray(open(S, 'rb').read()); b[27] ^= 0xFF
        self.assertTrue(save.source_damage(bytes(b)))
    def test_basicfileinfo_extension_dot_flip_flagged(self):
        import olefile, shutil, tempfile
        t = tempfile.mkdtemp() + '/x.rte'; shutil.copy(S, t)
        o = olefile.OleFileIO(t, write_mode=True); d = bytearray(o.openstream('BasicFileInfo').read())
        j = bytes(d).find('.rte'.encode('utf-16le')); self.assertGreater(j, 0); d[j] ^= 0xFF
        o.write_stream('BasicFileInfo', bytes(d)); o.close()
        self.assertTrue(save.source_damage(open(t, 'rb').read()))
if __name__ == '__main__': unittest.main()
