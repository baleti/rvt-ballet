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
        for off in (0x20, 0x38, 0x39, 0x3a, 0x3b, 0x44, 0x60, 0x64, 0x68, 0x6c, 0x70, 0x80, 0x100, 0x1f0, 0x48, 0x4c):
            b = bytearray(open(S, 'rb').read()); b[off] ^= 0xFF
            self.assertTrue(save.source_damage(bytes(b)), hex(off))
    def test_vm_tolerated_header_flips_not_flagged(self):
        for off in (0x10, 0x14, 0x18, 0x1c, 0x1d, 0x08, 0x18, 0x22, 0x34):     # Revit 2024 opened these clean
            b = bytearray(open(S, 'rb').read()); b[off] ^= 0xFF
            self.assertEqual(save.source_damage(bytes(b)), [], hex(off))
if __name__ == '__main__': unittest.main()

class Struct(unittest.TestCase):
    """c7x-rvtread 98/100: Revit 2024 REFUSED each of these (VM): FAT sector count 0x2c, first dir sector 0x30, mini-FAT start 0x3c, root entry type, sibling index past the table. Tolerated ones must stay unflagged."""
    @classmethod
    def setUpClass(cls):
        cls.src = open(S, 'rb').read()
    def _bad(self, edit):
        import struct
        b = bytearray(self.src); edit(b)
        ssz = 1 << struct.unpack_from('<H', b, 30)[0]
        return save._cfb_structure_bad(bytes(b), ssz, len(b) // ssz, struct.unpack_from('<I', b, 44)[0], 0, struct.unpack_from('<I', b, 72)[0])
    def _dir0(self):
        import struct
        ssz = 1 << struct.unpack_from('<H', self.src, 30)[0]
        return (struct.unpack_from('<I', self.src, 48)[0] + 1) * ssz
    def test_clean(self): self.assertEqual(self._bad(lambda b: None), [])
    def test_header_fields(self):
        for off in (0x2c, 0x30, 0x3c):
            def e(b, off=off): b[off] ^= 0xFF
            self.assertTrue(self._bad(e), hex(off))
    def test_root_type(self):
        d = self._dir0()
        def e(b): b[d + 66] ^= 0xFF
        self.assertTrue(self._bad(e))
    def test_sibling_out_of_range(self):
        d = self._dir0()
        def e(b): b[d + 128 + 75] = 0xFA
        self.assertTrue(self._bad(e))
    def test_tolerated_root_color_clsid(self):
        d = self._dir0()
        for o in (67, 80, 100):
            def e(b, o=o): b[d + o] ^= 0xFF
            self.assertEqual(self._bad(e), [], o)

class FatLoop(unittest.TestCase):
    def test_fat_self_loop_flagged(self):
        # c7x-rvtread 101: FAT entry 8 -> 8 (bit flip) made the CFB walk raise; source_damage used to answer [] (clean)
        import struct
        b = bytearray(open(S, 'rb').read()); sec = struct.unpack_from('<I', b, 76)[0]; ssz = 1 << struct.unpack_from('<H', b, 30)[0]
        off = (sec + 1) * ssz; e = struct.unpack_from('<I', b, off + 32)[0]
        struct.pack_into('<I', b, off + 32, 8)
        self.assertTrue(save.source_damage(bytes(b)))

class CrossLink(unittest.TestCase):
    def test_cross_linked_chain_flagged(self):
        # c7x-rvtread 102: a stream's chain ends in another stream's sectors: parses, wrong data
        import struct
        b = bytearray(open(S, 'rb').read()); ssz = 1 << struct.unpack_from('<H', b, 30)[0]; per = ssz // 4
        sec = struct.unpack_from('<I', b, 76)[0]; fat = struct.unpack_from('<%dI' % per, b, (sec + 1) * ssz)
        dch = struct.unpack_from('<I', b, 48)[0]; raw = bytes(b[(dch + 1) * ssz:(dch + 2) * ssz])
        big = [(struct.unpack_from('<I', raw, 128 * i + 116)[0], struct.unpack_from('<Q', raw, 128 * i + 120)[0]) for i in range(1, 32) if raw[128 * i + 66] == 2 and struct.unpack_from('<Q', raw, 128 * i + 120)[0] >= 4096]
        self.assertGreaterEqual(len(big), 2)
        (a, _), (c, _) = big[0], big[1]
        struct.pack_into('<I', b, (sec + 1) * ssz + 4 * a, c)      # first stream's first sector now continues into the second stream
        r = save._cfb_structure_bad(bytes(b), ssz, len(b) // ssz, struct.unpack_from('<I', b, 44)[0], 0, 0)
        self.assertTrue(r, r)
    def test_clean_chains_not_flagged(self):
        import struct
        b = open(S, 'rb').read(); ssz = 1 << struct.unpack_from('<H', b, 30)[0]
        self.assertEqual(save._cfb_structure_bad(b, ssz, len(b) // ssz, struct.unpack_from('<I', b, 44)[0], 0, 0), [])

class OutputGate(unittest.TestCase):
    def test_refuse_bad_output(self):
        b = bytearray(open(S, 'rb').read()); b[0x30] ^= 0xFF
        with self.assertRaises(save.OutputUnreadable): save._refuse_bad_output(bytes(b))
        save._refuse_bad_output(open(S, 'rb').read())

class BfiFlag(unittest.TestCase):
    def test_bfi_flag_byte_flip_flagged(self):
        # c7x-rvtread 110: Revit 2024 refused (InternalException) a BasicFileInfo with the byte before the 'Autodesk Revit' length flipped
        import olefile, shutil, tempfile
        t = tempfile.mkdtemp() + '/x.rte'; shutil.copy(S, t)
        o = olefile.OleFileIO(t, write_mode=True); d = bytearray(o.openstream('BasicFileInfo').read())
        j = bytes(d).find('Autodesk Revit'.encode('utf-16le')); self.assertGreater(j, 5); d[j - 5] ^= 0xFF
        o.write_stream('BasicFileInfo', bytes(d)); o.close()
        self.assertIn(('BasicFileInfo (structure)', 0), save.source_damage(open(t, 'rb').read()))
