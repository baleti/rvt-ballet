"""SAVE AS destination names that Windows would mangle or treat as devices are refused on every OS (nothing written)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import plat, save
F = plat.fsio.bad_filename

class T(unittest.TestCase):
    def test_names(self):
        for n in ('CON.rvt', 'con.rvt', 'NUL', 'com1.txt.rvt', 'LPT9.rvt', 'a.rvt.', 'a.rvt ', 'a:b.rvt', 'a?.rvt', 'x*.rvt', 'a\x01.rvt', 'a|b.rvt', 'é' * 130 + '.rvt', '', '..', 'CONIN$.rvt'):
            self.assertTrue(F(n), n)
        for n in ('Plan A.rvt', 'Ünï 日本.rvt', 'console.rvt', 'com10.rvt', 'a.b.c.rvt', 'AUXILIARY.rvt', '.hidden.rvt'):
            self.assertEqual(F(n), '', n)
    def test_dest_refused(self):
        d = os.path.dirname(os.path.abspath(__file__)); src = os.path.join(d, 'x.rvt')
        with self.assertRaises(save.BadDest) as c: save.check_dest(os.path.join(d, 'CON.rvt'), src)
        self.assertIn('reserved', str(c.exception))
        save.check_dest(os.path.join(d, 'ok name.rvt'), src)

if __name__ == '__main__': unittest.main()
