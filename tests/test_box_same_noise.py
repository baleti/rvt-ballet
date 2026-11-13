import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rvtballet.save import _box_same


def test_noise_is_same():
    b0 = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    assert _box_same(b0, ((1e-14, 0.0, 0.0), (1.0 + 1e-14, 1.0, 1.0)))


def test_real_shift_is_not_same():
    b0 = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    assert not _box_same(b0, ((2.0, 0.0, 0.0), (3.0, 1.0, 1.0)))
    assert not _box_same(b0, ((1e-6, 0.0, 0.0), (1.0, 1.0, 1.0)))
