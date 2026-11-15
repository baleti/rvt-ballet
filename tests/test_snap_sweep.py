import os, time, tempfile
from rvtballet import save

def test_sweep_removes_only_old_own_snap_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path))
    old = tmp_path / 'rvtballet-snap-old'; new = tmp_path / 'rvtballet-snap-new'; other = tmp_path / 'keep-me'
    for d in (old, new, other): d.mkdir(); (d / 'in.rvt').write_bytes(b'x')
    t = time.time() - 7 * 3600; os.utime(old, (t, t)); os.utime(other, (t, t))
    save._sweep_stale_snaps()
    assert not old.exists() and new.exists() and other.exists()


def test_sweep_also_removes_old_rb_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path))
    old = tmp_path / 'rvtballet-rb-old'; new = tmp_path / 'rvtballet-rb-new'
    for d in (old, new): d.mkdir(); (d / 'x.rvt').write_bytes(b'x')
    t = time.time() - 7 * 3600; os.utime(old, (t, t))
    save._sweep_stale_snaps()
    assert not old.exists() and new.exists()
