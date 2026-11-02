"""A failure found AFTER the model file was replaced must not claim 'the model file was not touched'."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rvtballet import save


class DiskError(Exception): pass


class PostCommit(unittest.TestCase):
    def test_after_rename_is_honest(self):
        m = save.user_message(DiskError('destination content differs after rename (filesystem problem): /x/a.rvt'), 500)
        self.assertIn('WAS replaced', m); self.assertIn('RESTORE', m); self.assertNotIn('not touched', m)

    def test_pre_commit_keeps_note(self):
        m = save.user_message(DiskError('save failed: [Errno 13] x'), 500)
        self.assertIn('not touched', m); self.assertNotIn('WAS replaced', m)


if __name__ == '__main__': unittest.main()
