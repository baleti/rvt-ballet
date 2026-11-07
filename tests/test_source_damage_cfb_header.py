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
    def test_vm_refused_header_flips_flagged(self):
        # c7x-rvtread 97: every one of these single-byte xor-0xFF flips was REFUSED by Revit 2024 in the VM while the reader loaded it
        for off in (0x20, 0x38, 0x39, 0x3a, 0x3b, 0x44, 0x60, 0x64, 0x68, 0x6c, 0x70, 0x80, 0x100, 0x1f0):
            b = bytearray(open(S, 'rb').read()); b[off] ^= 0xFF
            self.assertTrue(save.source_damage(bytes(b)), hex(off))
    def test_vm_tolerated_header_flips_not_flagged(self):
        for off in (0x10, 0x14, 0x18, 0x1c, 0x1d):     # Revit 2024 opened these clean
            b = bytearray(open(S, 'rb').read()); b[off] ^= 0xFF
            self.assertEqual(save.source_damage(bytes(b)), [], hex(off))
if __name__ == '__main__': unittest.main()
