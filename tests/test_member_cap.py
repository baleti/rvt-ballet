import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import rvt_member_cap as M
def test_ok_sizes():
    assert M.oversized([131088, 100, 0, 131071]) == []
def test_merged_member_flagged():      # 2026 add: two members 131088 + 107484 merged by the writer
    assert M.oversized([5, 131088 + 107484, 7]) == [(1, 238572)]
