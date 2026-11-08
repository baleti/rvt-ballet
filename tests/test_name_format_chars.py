"""c5x-rvtread: invisible format characters (U+FEFF, U+200B, U+202E) in element names are refused; normal accents stay allowed."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import edit
class T(unittest.TestCase):
    def test_refused(self):
        for n in ('Lev﻿1', 'a​b', 'Lev‮1'):
            with self.assertRaises(edit.EditError): edit._check_element_name(n)
    def test_allowed(self):
        for n in ('Café', 'Café', 'Level 1 äöü', 'T.O. Slab'):
            edit._check_element_name(n)
class S(unittest.TestCase):
    def test_edge_spaces_refused(self):
        for n in (' lead', 'trail ', ' both '):
            with self.assertRaises(edit.EditError): edit._check_element_name(n)
        edit._check_element_name('in ner')
    def test_dots_only_refused(self):
        for n in ('.', '..', '...'):
            with self.assertRaises(edit.EditError): edit._check_element_name(n)
        edit._check_element_name('T.O. Slab')
class N(unittest.TestCase):
    def test_nfc_nfd_batch_duplicate(self):
        mk = lambda e, v: {'op': 'set_string', 'eid': e, 'field': 'DatumPlane.m_text', 'value': v}
        with self.assertRaises(edit.EditError): edit._check_batch_names([mk(1, 'Café'), mk(2, 'Café')])
        edit._check_batch_names([mk(1, 'Cafe'), mk(2, 'Café')])
if __name__ == '__main__': unittest.main()
