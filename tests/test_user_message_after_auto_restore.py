"""after a successful automatic restore the user text must not say the file may be damaged / needs RESTORE; if the restore failed it must. Synthetic."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rvtballet import save
BASE = "destination content differs after rename (filesystem problem): x; "
def test_restored():
    m = save.user_message(Exception(BASE + "the previous version was restored from its backup"))
    assert "nothing more to restore" in m and "may be damaged" not in m
def test_restore_failed():
    m = save.user_message(Exception(BASE + "RESTORE FAILED (e); backup: b"))
    assert "may be damaged" in m and "use RESTORE" in m
