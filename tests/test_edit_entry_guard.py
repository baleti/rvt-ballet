import os, shutil, time
import pytest
from rvtballet import editcli
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason='Autodesk sample missing')


def _edit(f, out):
    msgs = []; rc = editcli.edit_main([str(f), '-o', str(out), '--delete', '1'], msgs.append); return rc, msgs


def test_edit_refuses_half_written_source(tmp_path):
    half = tmp_path / 'b.rvt'; half.write_bytes(open(SRC, 'rb').read()[:3 << 20]); t = time.time() - 100; os.utime(half, (t, t))
    rc, m = _edit(half, tmp_path / 'o.rvt')
    assert rc != 0 and not (tmp_path / 'o.rvt').exists(), m


def test_edit_refuses_source_modified_a_moment_ago(tmp_path, monkeypatch):
    f = tmp_path / 'c.rvt'; shutil.copyfile(SRC, f)          # mtime = now: a save may still be running
    from rvtballet import stable
    monkeypatch.setattr(stable, 'wait_quiet', lambda *a, **k: (_ for _ in ()).throw(stable.InUse(str(f), 'still being saved')))
    rc, m = _edit(f, tmp_path / 'o.rvt')
    assert rc == 75 and not (tmp_path / 'o.rvt').exists(), m
