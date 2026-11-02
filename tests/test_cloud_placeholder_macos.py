"""macOS: a dataless (iCloud-evicted) file counts as a cloud placeholder; a normal file does not; no st_flags (Linux) is False. Faked os.stat, runs anywhere."""
import os, sys
from types import SimpleNamespace
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import plat

def test_dataless_flag():
    f = plat.fsio
    with mock.patch.object(f.sys, 'platform', 'darwin'):
        with mock.patch.object(f.os, 'stat', return_value=SimpleNamespace(st_flags=0x40000000)): assert f.is_cloud_placeholder('/x/a.rvt') is True
        with mock.patch.object(f.os, 'stat', return_value=SimpleNamespace(st_flags=0)): assert f.is_cloud_placeholder('/x/a.rvt') is False
        with mock.patch.object(f.os, 'stat', return_value=SimpleNamespace()): assert f.is_cloud_placeholder('/x/a.rvt') is False      # no st_flags
        with mock.patch.object(f.os, 'stat', side_effect=OSError): assert f.is_cloud_placeholder('/x/a.rvt') is False

def test_linux_never():
    assert plat.fsio.is_cloud_placeholder(__file__) is False if sys.platform.startswith('linux') else True
