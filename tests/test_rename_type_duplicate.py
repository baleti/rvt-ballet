"""c5x-rvtread item 20: renaming a type onto the name of a sibling type of the same family is refused (case-insensitive, NFC); a fresh name or a name used in another family passes the check. 2026 write-lab scene (reader exposes FamilySymbol 'Type Name'/'Family Name')."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/2026_writer_house1.rte')
@unittest.skipUnless(os.path.exists(S), 'scene absent')
class T(unittest.TestCase):
    mk = lambda self, v, e=19014: {'op': 'set_string', 'eid': e, 'field': 'SymbolInfo.m_name', 'value': v}
    def test_sibling_name_refused(self):
        for v in ('0406 x 1220mm', '0406 X 1220MM'):
            with self.assertRaises(edit.EditError): edit._check_symbol_name_unique(S, self.mk(v))
    def test_fresh_name_passes(self):
        edit._check_symbol_name_unique(S, self.mk('C5X fresh type'))
    def test_own_name_passes(self):
        edit._check_symbol_name_unique(S, self.mk('0406 x 0610mm'))
    def test_non_symbol_ignored(self):
        edit._check_symbol_name_unique(S, self.mk('0406 x 1220mm', e=303741))
if __name__ == '__main__': unittest.main()
