import sys, types
import numpy as np
from unittest import mock

def test_wall_openings_without_ocp_returns_empty():
    from rvtballet import build
    ctx = types.SimpleNamespace(hosted={"w": ["door"]})
    with mock.patch.dict(sys.modules, {"OCP": None, "OCP.gp": None, "rvtballet.occ": None}):
        out = build.wall_openings(ctx, "w", np.zeros(3), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0]), np.array([1.0, 0.2, 3.0]))
    assert out == []
