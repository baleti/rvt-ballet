import os
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rvtballet import vcache


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    cache.mkdir()
    sheets = tmp_path / "rvtsheets"
    sheets.mkdir()
    (sheets / "alpha.py").write_text("VALUE = 1\n")
    (sheets / "beta.py").write_text("VALUE = 2\n")
    monkeypatch.setattr(vcache, "CACHE", str(cache))
    monkeypatch.setattr(vcache, "SHEETS", str(tmp_path))
    monkeypatch.setattr(vcache, "_stamp", None)


def source(tmp_path, name="drawing.rvt", content=b"model"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def cached_file(src, req, stamp, mtime):
    path = Path(vcache.CACHE) / f"{vcache._base(src, req)}.{stamp}.json"
    path.write_text("{}")
    os.utime(path, (mtime, mtime))
    return str(path)


def test_code_stamp_is_ten_hex_characters():
    assert re.fullmatch(r"[0-9a-f]{10}", vcache.code_stamp())


def test_code_stamp_is_stable_after_recomputation(monkeypatch):
    stamp = vcache.code_stamp()
    monkeypatch.setattr(vcache, "_stamp", None)
    assert vcache.code_stamp() == stamp


def test_code_stamp_is_stored_and_reused(tmp_path):
    stamp = vcache.code_stamp()
    assert vcache._stamp == stamp
    (tmp_path / "rvtsheets" / "alpha.py").write_text("VALUE = 9\n")
    assert vcache.code_stamp() == stamp
    assert vcache._stamp == stamp


@pytest.mark.parametrize("filename", ["alpha.py", "beta.py"])
def test_code_stamp_changes_with_each_python_file(tmp_path, monkeypatch, filename):
    stamp = vcache.code_stamp()
    # Same-length changes distinguish content hashing from file-size hashing.
    (tmp_path / "rvtsheets" / filename).write_text("VALUE = 9\n")
    monkeypatch.setattr(vcache, "_stamp", None)
    assert vcache.code_stamp() != stamp


def test_code_stamp_ignores_non_python_files(tmp_path, monkeypatch):
    stamp = vcache.code_stamp()
    notes = tmp_path / "rvtsheets" / "notes.txt"
    notes.write_text("initial notes")
    monkeypatch.setattr(vcache, "_stamp", None)
    assert vcache.code_stamp() == stamp
    notes.write_text("changed notes with a different length")
    monkeypatch.setattr(vcache, "_stamp", None)
    assert vcache.code_stamp() == stamp


def test_base_ignores_source_directory(tmp_path):
    first = source(tmp_path, "first/drawing.rvt")
    second = source(tmp_path, "second/drawing.rvt")
    assert vcache._base(first, {"view": 1}) == vcache._base(second, {"view": 1})


def test_base_changes_with_basename(tmp_path):
    first = source(tmp_path, "first.rvt")
    second = source(tmp_path, "second.rvt")
    assert vcache._base(first, {}) != vcache._base(second, {})


def test_base_changes_with_size(tmp_path):
    src = source(tmp_path)
    base = vcache._base(src, {})
    src.write_bytes(b"larger model")
    assert vcache._base(src, {}) != base


def test_base_changes_with_request(tmp_path):
    src = source(tmp_path)
    assert vcache._base(src, {"view": 1}) != vcache._base(src, {"view": 2})


def test_base_ignores_request_key_order(tmp_path):
    src = source(tmp_path)
    first = {"view": 1, "options": {"width": 100, "height": 200}}
    second = {"options": {"height": 200, "width": 100}, "view": 1}
    assert vcache._base(src, first) == vcache._base(src, second)


def test_cache_fn_joins_cache_base_and_stamp(tmp_path):
    src = source(tmp_path)
    req = {"view": 1}
    expected = os.path.join(
        vcache.CACHE, f"{vcache._base(src, req)}.{vcache.code_stamp()}.json"
    )
    assert vcache.cache_fn(src, req) == expected


def test_best_fn_returns_none_for_empty_cache(tmp_path):
    assert vcache.best_fn(source(tmp_path), {"view": 1}) is None


def test_best_fn_selects_newest_mtime_across_stamps(tmp_path):
    src = source(tmp_path)
    req = {"view": 1}
    cached_file(src, req, "ffffffffff", 100)
    newest = cached_file(src, req, "1111111111", 300)
    cached_file(src, req, "aaaaaaaaaa", 200)
    assert vcache.best_fn(src, req) == newest


def test_best_fn_ignores_newer_files_for_other_requests(tmp_path):
    src = source(tmp_path)
    expected = cached_file(src, {"view": 1}, "1111111111", 100)
    cached_file(src, {"view": 2}, "2222222222", 500)
    assert vcache.best_fn(src, {"view": 1}) == expected


def test_best_fn_returns_none_when_only_other_requests_are_cached(tmp_path):
    src = source(tmp_path)
    cached_file(src, {"view": 2}, "2222222222", 500)
    assert vcache.best_fn(src, {"view": 1}) is None
