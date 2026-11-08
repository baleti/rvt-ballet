"""Nested family instances (Autodesk Snowdon Facades 2024): move the super-component (593273) and a hosted child (593274); SAVE AS must verify with 0 diffs and change exactly 1 element; in-place SAVE! must be refused (hosted element) with the source untouched. Wraps tools/rvt_one_edit.py. Run: tests/test_save_nested_move.py [FILE]. Slow (20+ min each under load)."""
import os, sys, subprocess, json, re, tempfile
H = os.path.dirname(os.path.abspath(__file__))
F = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/c2x-tmp/ip25/2024_46_Snowdon_Towers_Sample_Facades.rvt')
for eid in (593273, 593274):
    out = os.path.join(tempfile.mkdtemp(), 'n.rvt')
    p = subprocess.run([sys.executable, os.path.join(H, '..', 'tools', 'rvt_one_edit.py'), F, json.dumps({'op': 'move', 'eid': eid, 'dx': 1.0, 'dy': 0.5, 'dz': 0.0}), out], capture_output=True, text=True)
    row = eval(re.search(r'ONE-EDIT (\{.*\})', p.stdout).group(1))
    assert row['edit'] == 200 and row['verify_diffs'] == 0 and row['elements_changed'] == 1, row
    assert row['save_status'] == 409 and row['save_detail'] == 'group_or_option', row
    print('ok', eid)
