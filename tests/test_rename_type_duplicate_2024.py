"""c5x-rvtread item 23: type-name uniqueness on a real Autodesk 2024 sample (Snowdon HVAC): reader exposes 197 FamilySymbols with Family Name + Type Name, so a rename onto a sibling's name (same family, case-insensitive) is refused; a fresh name passes."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import edit
S = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
@unittest.skipUnless(os.path.exists(S), 'sample absent')
class T(unittest.TestCase):
    @classmethod
    def setUpClass(c):
        for p in ('~/rvt-research', '~/rvt-research/write-lab'): sys.path.insert(0, os.path.expanduser(p))
        import rvt_params; P = rvt_params.params(S); c.pair = None
        by = {}
        for e, d in P.items():
            if isinstance(d, dict) and d.get('class') == 'FamilySymbol':
                q = d.get('params') or {}; by.setdefault(q.get('Family Name'), []).append((e, q.get('Type Name')))
        for fam, l in by.items():
            if fam and len(l) >= 2: c.pair = (l[0], l[1]); break
    mk = lambda self, e, v: {'op': 'set_string', 'eid': e, 'field': 'SymbolInfo.m_name', 'value': v}
    def test_sibling_refused(self):
        (a, an), (b, bn) = self.pair
        for v in (bn, str(bn).upper()):
            with self.assertRaises(edit.EditError): edit._check_symbol_name_unique(S, self.mk(a, v))
    def test_fresh_and_own_pass(self):
        (a, an), _ = self.pair
        edit._check_symbol_name_unique(S, self.mk(a, 'C5X fresh type')); edit._check_symbol_name_unique(S, self.mk(a, an))
if __name__ == '__main__': unittest.main()
