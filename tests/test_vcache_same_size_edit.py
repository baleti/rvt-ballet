import os
from rvtballet import vcache

def test_same_size_edit_changes_the_cache_key(tmp_path):
    f = tmp_path / 'm.rvt'; f.write_bytes(b'A' * 200000)
    k1 = vcache.cache_fn(str(f), {'op': 'views'})
    g = tmp_path / 'copy' / 'm.rvt'; g.parent.mkdir(); g.write_bytes(f.read_bytes()); os.utime(g, (1, 1))
    assert vcache.cache_fn(str(g), {'op': 'views'}) == k1          # a copy (other mtime) keeps its cache
    b = bytearray(f.read_bytes()); b[10] = ord('B'); f.write_bytes(bytes(b))     # same size, different content in the head block
    assert vcache.cache_fn(str(f), {'op': 'views'}) != k1
