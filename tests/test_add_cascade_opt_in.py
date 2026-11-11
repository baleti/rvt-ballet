"""INS_MERGE_CASCADE: a 2023 FI ADD whose insert does not fit the first partition member is REFUSED by default (layout guard) and only built with the
opt-in INS_MERGE_CASCADE=1; the opt-in output must pass the source damage gate. NOT a Revit verdict (the Revit VM judge of the cascade layout is pending).
Needs $RVT_ADD_SAMPLE_2023 (Autodesk rst_basic 2023) and $RVT_ADD_SRC_2023 (a registered, childless FamilyInstance id, e.g. 512451)."""
import os, sys, subprocess, tempfile, unittest
S = os.environ.get('RVT_ADD_SAMPLE_2023'); SRC = os.environ.get('RVT_ADD_SRC_2023', '512451')
TOOL = os.path.join(os.path.dirname(__file__), '..', 'tools', 'rvt_add_clone.py'); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
@unittest.skipUnless(S and os.path.exists(S), 'RVT_ADD_SAMPLE_2023 not set')
class T(unittest.TestCase):
    def test_default_refuses_cascade_builds_clean(self):
        from rvtballet.save import source_damage
        with tempfile.TemporaryDirectory() as d:
            o1, o2 = os.path.join(d, 'a.rvt'), os.path.join(d, 'c.rvt')
            r = subprocess.run([sys.executable, TOOL, S, o1, '--src', SRC], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertFalse(os.path.exists(o1))
            r = subprocess.run([sys.executable, TOOL, S, o2, '--src', SRC], capture_output=True, text=True, env=dict(os.environ, INS_MERGE_CASCADE='1'))
            self.assertEqual(r.returncode, 0, r.stderr[-300:]); self.assertEqual(source_damage(open(o2, 'rb').read()), [])
if __name__ == '__main__': unittest.main()
