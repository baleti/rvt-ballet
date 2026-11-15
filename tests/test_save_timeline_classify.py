import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from rvt_save_timeline_classify import classify

H = lambda *rows: [dict(zip(('t_ms', 'name', 'length', 'lastwrite_ticks', 'fileindex'), r)) for r in rows]

def test_in_place_steps():
    assert classify(H((0, 'm.rvt', '100', '1', 'a'), (40, 'm.rvt', '150', '2', 'a'), (80, 'm.rvt', '200', '3', 'a')), 'm.rvt')[0] == 'in-place-overwrite-in-steps'
def test_truncate():
    assert classify(H((0, 'm.rvt', '100', '1', 'a'), (40, 'm.rvt', '0', '2', 'a'), (80, 'm.rvt', '90', '3', 'a')), 'm.rvt')[0] == 'truncate-then-rewrite'
def test_rename():
    r = classify(H((0, 'm.rvt', '100', '1', 'a'), (40, 'm.0001.rvt', '100', '2', 'b'), (80, 'm.rvt', '120', '3', 'c')), 'm.rvt'); assert r[0] == 'replace-by-rename' and r[1]['side_files'] == ['m.0001.rvt']
def test_nothing():
    assert classify(H((0, 'm.rvt', '100', '1', 'a')), 'm.rvt')[0] == 'no-change-seen'
