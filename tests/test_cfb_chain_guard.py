"""A corrupt FAT (loop or huge run) must make the CFB reader fail fast instead of allocating GBs (found by a one-bit flip fuzz of a 22 MB 2024 file: 12 GB peak before the refusal)."""
import os, sys, types, pytest
LIB = os.environ.get('SAVEGATE_RVT_LIB') or os.path.expanduser('~/rvt-research/write-lab')
if not os.path.isfile(os.path.join(LIB, 'cfb.py')): pytest.skip('write-lab cfb.py not available', allow_module_level=True)
sys.path.insert(0, LIB)
import cfb


def _stub(fat, minifat=None, nbuf=8 * 512):
    o = types.SimpleNamespace(buf=bytes(nbuf), ss=512, fat=fat, minifat=minifat or [], mss=64, ministream=bytes(4096), cutoff=4096)
    o._sec = lambda i: bytes(512)
    return o


def test_fat_loop_is_refused_fast():
    o = _stub([1, 0])            # sector 0 -> 1 -> 0 -> ... forever
    with pytest.raises(AssertionError): cfb.CFB._chain(o, 0)


def test_valid_chain_still_read():
    o = _stub([1, 2, 0xFFFFFFFE])
    assert len(cfb.CFB._chain(o, 0)) == 3 * 512


def test_minifat_loop_is_refused_fast():
    o = _stub([], minifat=[1, 0]); o._chain = lambda s: b''
    e = types.SimpleNamespace(size=100, start=0)
    with pytest.raises(AssertionError): cfb.CFB._read(o, e)
