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
if __name__ == '__main__': unittest.main()
