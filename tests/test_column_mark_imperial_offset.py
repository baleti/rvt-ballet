"""a column move rewrites the derived Column Location Mark; imperial offsets (found on Structural 2024 HSS column) must be accepted, a changed grid name must not"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save

def test_imperial_offset_changes():
    assert save._same_mark_base('C(6\'-4 3/4")-8(9\'-6 1/2")', 'C(6\'-4 3/4")-8(10\'-6 1/2")')
    assert save._same_mark_base('C(6\'-4 3/4")-8(9\'-6 1/2")', 'C(7\'-4 3/4")-8(9\'-6 1/2")')

def test_grid_name_change_still_refused():
    assert not save._same_mark_base('C(6\'-4 3/4")-8(9\'-6 1/2")', 'D(6\'-4 3/4")-8(9\'-6 1/2")')
    assert not save._same_mark_base('C(6\'-4 3/4")-8(9\'-6 1/2")', 'C(6\'-4 3/4")-9(9\'-6 1/2")')

def test_existing_metric_cases():
    assert save._same_mark_base('D-1', 'D-1(610)')
    assert save._same_mark_base('W(137)-16(1162)', 'W(137)-16(1467)')
    assert not save._same_mark_base('D-1', 'E-1(610)')

def test_diagonal_move_off_grid_intersection():
    assert save._same_mark_base('D-3', 'D(1\'-0")-3(1\'-0")')
    assert not save._same_mark_base('D-3', 'E(1\'-0")-3(1\'-0")')
    assert not save._same_mark_base('D-3', 'D(1\'-0")-4(1\'-0")')
