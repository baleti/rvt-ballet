import json
from pathlib import Path
import struct
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rvtviewer.glb import _lin, to_yup_m, write_glb


def _batch(**overrides):
    batch = {
        "name": "triangle",
        "color": (0.0, 0.5, 1.0, 1.0),
        "pos": np.array([[-2, 3, 0.5], [4, -1, 2], [0, 5, -3]], dtype=np.float32),
        "eidx": np.array([7, 8, 9], dtype=np.float32),
        "idx": np.array([2, 0, 1], dtype=np.int32),
    }
    batch.update(overrides)
    return batch


def _read_glb(path):
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data)
    assert magic == b"glTF"
    assert version == 2
    assert total == len(data)
    assert total % 4 == 0
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    assert json_type == b"JSON"
    assert json_length % 4 == 0
    json_end = 20 + json_length
    json_bytes = data[20:json_end]
    assert len(json_bytes) == json_length
    text = json_bytes.decode("utf-8")
    document, end = json.JSONDecoder().raw_decode(text)
    unpadded_length = len(text[:end].encode("utf-8"))
    assert json_bytes[unpadded_length:] == b" " * ((-unpadded_length) % 4)
    bin_length, bin_type = struct.unpack_from("<I4s", data, json_end)
    assert bin_type == b"BIN\0"
    assert bin_length % 4 == 0
    binary = data[json_end + 8:]
    assert len(binary) == bin_length
    assert total == 12 + 8 + json_length + 8 + bin_length
    assert document["buffers"] == [{"byteLength": bin_length}]
    return document, binary


def _write(tmp_path, batches, **kwargs):
    path = tmp_path / "output.glb"
    write_glb(path, batches, **kwargs)
    return _read_glb(path)


def _primitive(document, mesh=0):
    primitives = document["meshes"][mesh]["primitives"]
    assert len(primitives) == 1
    return primitives[0]


def _assert_accessor(document, binary, index, expected, component_type, kind, target):
    accessor = document["accessors"][index]
    assert accessor["componentType"] == component_type
    assert accessor["type"] == kind
    assert accessor["count"] == len(expected)
    view = document["bufferViews"][accessor["bufferView"]]
    assert view["buffer"] == 0
    assert view["target"] == target
    assert view["byteLength"] == expected.nbytes
    start = view["byteOffset"] + accessor.get("byteOffset", 0)
    raw = binary[start:start + expected.nbytes]
    assert raw == expected.tobytes()
    actual = np.frombuffer(raw, dtype=expected.dtype).reshape(expected.shape)
    np.testing.assert_array_equal(actual, expected)


def test_header_and_chunk_lengths(tmp_path):
    document, binary = _write(tmp_path, [_batch()])
    assert document["asset"]["version"] == "2.0"
    assert binary


def test_json_padding_is_spaces(tmp_path):
    # Changing a top-level string by one byte exercises every padding length.
    observed = set()
    for size in range(4):
        _write(tmp_path, [_batch()], extras={"label": "x" * size})
        data = (tmp_path / "output.glb").read_bytes()
        length = struct.unpack_from("<I", data, 12)[0]
        payload = data[20:20 + length]
        padding = payload[len(payload.rstrip(b" ")):]
        observed.add(len(padding))
        assert padding == b" " * len(padding)
    assert observed == {0, 1, 2, 3}


def test_one_node_mesh_and_material_per_nonempty_batch(tmp_path):
    batches = [_batch(name="first"), _batch(name="second")]
    document, _ = _write(tmp_path, batches)
    for key in ("nodes", "meshes", "materials"):
        assert len(document[key]) == 2
        assert [item["name"] for item in document[key]] == ["first", "second"]
    assert document["scenes"][document["scene"]]["nodes"] == [0, 1]
    for index in range(2):
        assert document["nodes"][index]["mesh"] == index
        assert _primitive(document, index)["material"] == index


def test_empty_batches_are_skipped(tmp_path):
    empty = _batch(name="empty", pos=np.empty((0, 3)), eidx=[], idx=[])
    document, _ = _write(tmp_path, [empty, _batch(name="kept"), empty])
    for key in ("nodes", "meshes", "materials"):
        assert len(document[key]) == 1
        assert document[key][0]["name"] == "kept"
    assert document["nodes"][0]["mesh"] == 0
    assert _primitive(document)["material"] == 0
    assert document["scenes"][0]["nodes"] == [0]
    assert len(document["accessors"]) == len(document["bufferViews"]) == 3


@pytest.mark.parametrize("batches", [[], [_batch(idx=[])], [
    _batch(pos=np.empty((0, 3)), eidx=[], idx=[]), _batch(idx=[])
]])
def test_all_empty_batches(tmp_path, batches):
    document, binary = _write(tmp_path, batches)
    for key in ("nodes", "meshes", "materials", "accessors", "bufferViews"):
        assert document[key] == []
    assert document["scenes"][document["scene"]]["nodes"] == []
    assert binary == b""


def test_position_bounds(tmp_path):
    batch = _batch()
    document, _ = _write(tmp_path, [batch])
    accessor = document["accessors"][_primitive(document)["attributes"]["POSITION"]]
    assert accessor["min"] == [-2.0, -1.0, -3.0]
    assert accessor["max"] == [4.0, 5.0, 2.0]


def test_position_buffer_contents(tmp_path):
    batch = _batch()
    document, binary = _write(tmp_path, [batch])
    index = _primitive(document)["attributes"]["POSITION"]
    _assert_accessor(document, binary, index, batch["pos"], 5126, "VEC3", 34962)


def test_element_index_buffer_contents(tmp_path):
    batch = _batch()
    document, binary = _write(tmp_path, [batch])
    index = _primitive(document)["attributes"]["_EIDX"]
    _assert_accessor(document, binary, index, batch["eidx"], 5126, "SCALAR", 34962)


def test_index_buffer_contents(tmp_path):
    batch = _batch()
    document, binary = _write(tmp_path, [batch])
    _assert_accessor(document, binary, _primitive(document)["indices"],
                     batch["idx"].astype("<u4"), 5125, "SCALAR", 34963)


@pytest.mark.parametrize("optional", [{}, {"mat": None, "nrm": None}])
def test_optional_attributes_absent(tmp_path, optional):
    document, _ = _write(tmp_path, [_batch(**optional)])
    assert set(_primitive(document)["attributes"]) == {"POSITION", "_EIDX"}
    assert len(document["accessors"]) == 3


@pytest.mark.parametrize("include_mat,include_nrm", [(True, False), (False, True), (True, True)])
def test_optional_attributes_present(tmp_path, include_mat, include_nrm):
    optional = {}
    if include_mat:
        optional["mat"] = np.array([2, 4, 6], dtype=np.float32)
    if include_nrm:
        optional["nrm"] = np.eye(3, dtype=np.float32)
    document, binary = _write(tmp_path, [_batch(**optional)])
    attrs = _primitive(document)["attributes"]
    assert set(attrs) == {"POSITION", "_EIDX"} | (
        {"_MAT"} if include_mat else set()) | ({"NORMAL"} if include_nrm else set())
    assert len(document["accessors"]) == 3 + include_mat + include_nrm
    for key, semantic, kind in [("mat", "_MAT", "SCALAR"), ("nrm", "NORMAL", "VEC3")]:
        if key in optional:
            _assert_accessor(document, binary, attrs[semantic], optional[key],
                             5126, kind, 34962)


def test_buffer_view_offsets_are_aligned(tmp_path):
    document, binary = _write(tmp_path, [
        _batch(mat=np.array([1, 2, 3]), nrm=np.eye(3)), _batch(name="second")
    ])
    previous_end = 0
    for view in document["bufferViews"]:
        start = view["byteOffset"]
        assert start % 4 == 0
        assert start == previous_end + (-previous_end) % 4
        assert binary[previous_end:start] == b"\0" * (start - previous_end)
        previous_end = start + view["byteLength"]
        assert previous_end <= len(binary)
    assert previous_end == len(binary)


def test_default_triangle_mode(tmp_path):
    document, _ = _write(tmp_path, [_batch()])
    assert _primitive(document)["mode"] == 4


def test_line_mode(tmp_path):
    document, _ = _write(tmp_path, [_batch(mode=1, idx=[0, 1, 1, 2])])
    assert _primitive(document)["mode"] == 1


def test_transparent_material(tmp_path):
    document, _ = _write(tmp_path, [_batch(color=(0.1, 0.2, 0.3, 0.25))])
    material = document["materials"][0]
    assert material["alphaMode"] == "BLEND"
    assert material["doubleSided"] is True
    assert material["pbrMetallicRoughness"]["baseColorFactor"][3] == 0.25


@pytest.mark.parametrize("value", [0.0, 0.04045, 0.5, 1.0])
def test_lin_matches_srgb_formula(value):
    expected = value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    assert _lin(value) == pytest.approx(expected, rel=1e-12, abs=1e-15)


def test_base_color_is_linear_with_unchanged_alpha(tmp_path):
    color = (0.04045, 0.5, 1.0, 0.37)
    document, _ = _write(tmp_path, [_batch(color=color)])
    actual = document["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
    expected = [0.04045 / 12.92, ((0.5 + 0.055) / 1.055) ** 2.4, 1.0, 0.37]
    assert actual == pytest.approx(expected, rel=1e-12)
    assert actual[3] == color[3]


def test_extras_at_top_level(tmp_path):
    extras = {"project": "sample", "elements": [12, 34], "metadata": {"units": "m"}}
    document, _ = _write(tmp_path, [_batch()], extras=extras)
    assert document["extras"] == extras


def test_to_yup_m_converts_axes_and_units():
    source = np.array([[1, 2, 3], [-4, 5, -6], [0, 0, 0]])
    actual = to_yup_m(source)
    np.testing.assert_allclose(actual, [
        [0.3048, 0.9144, -0.6096],
        [-1.2192, -1.8288, -1.524],
        [0, 0, 0],
    ], rtol=1e-12, atol=1e-15)
