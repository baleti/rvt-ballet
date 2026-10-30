import os
from unittest import mock
import pytest
from rvtballet import save, plat

def test_gate_refuses_placeholder(tmp_path):
    f = tmp_path / "a.rvt"; f.write_bytes(b"x")
    with mock.patch.object(plat.fsio, "is_cloud_placeholder", lambda p: p == str(f)):
        with pytest.raises(save.CloudPlaceholder, match="online-only"):
            save.save_as(None, "m", str(f), str(tmp_path / "b.rvt"))
        with pytest.raises(save.CloudPlaceholder):
            save.save_overwrite(None, "m", str(f))
    assert sorted(os.listdir(tmp_path)) == ["a.rvt"]
    assert save.error_status(save.CloudPlaceholder("x")) == (409, "cloud_placeholder")
