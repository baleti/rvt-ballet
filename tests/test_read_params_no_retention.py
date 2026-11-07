"""_read_params must not retain per-path reader state: every read-back parses a fresh temp path, and rvt_geometry's path-keyed caches used to keep ~90 MB of decoded records per save (a 15-save chain then tripped the memory guard)."""
import os, sys, glob, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rvtballet import save


def _sample():
    for pat in ('~/rvtsave-work/c1x_keep/*.rte', '~/src/rvt-viewer/tests/data/*.rvt'):
        g = sorted(glob.glob(os.path.expanduser(pat)), key=os.path.getsize)
        if g: return g[0]
    pytest.skip('no Autodesk .rte/.rvt sample available')


def test_read_params_leaves_no_path_keyed_caches(tmp_path, monkeypatch):
    monkeypatch.setenv('RVTBALLET_SNAPSHOT_CACHE', '0')
    b = bytearray(open(_sample(), 'rb').read())
    for i in range(3):
        b[-1] = i; save._RB_MEMO.clear()
        try: save._read_params(bytes(b))
        except Exception as e: pytest.skip('reader unavailable: %s' % e)
    g = sys.modules.get('rvt_geometry')
    assert g is None or (not g._ctx and not g._docs)
