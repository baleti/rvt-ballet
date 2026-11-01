"""c4x-rvtmatrix: a source truncated BEFORE load must give a clean 409 source_damaged on edit (was a bare 500), nothing written. Synthetic: needs no real file, the reader's refusal is faked via a truncated copy of any RVT if present."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import save as savemod

class T(unittest.TestCase):
    def test_valueerror_truncated_maps_to_409(self):
        class SS:
            def doc(self, mid, src): raise ValueError('file truncated: directory needs 10 bytes, file has 5')
            def edits(self, mid): return None
        from unittest import mock
        with mock.patch('rvtballet.edit.validate_op', lambda o: o):
            with self.assertRaises(savemod.SourceDamaged) as cx: savemod.add_edit(SS(), 'm', '/x', {'op': 'noop'})
        self.assertEqual(savemod.error_status(cx.exception)[0], 409)
        self.assertIn('nothing was written', str(cx.exception))
    def test_other_valueerror_unchanged(self):
        class SS:
            def doc(self, mid, src): raise ValueError('bad thing')
            def edits(self, mid): return None
        from unittest import mock
        with mock.patch('rvtballet.edit.validate_op', lambda o: o):
            with self.assertRaises(ValueError): savemod.add_edit(SS(), 'm', '/x', {'op': 'noop'})
if __name__ == '__main__': unittest.main()
