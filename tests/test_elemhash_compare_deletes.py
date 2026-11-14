"""rvt_elemhash_compare: a deleted element passes only when its id is declared in the allowed list (synthetic data)."""
import os, subprocess, sys
T = os.environ.get('CMP') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_elemhash_compare.py')  # CMP overrides to check the test fails on the pre-fix tool
def run(tmp_path, a, b, allowed):
    pa, pb = tmp_path / 'a.txt', tmp_path / 'b.txt'
    pa.write_text(''.join('EH %d %08x\n' % (k, v) for k, v in a.items())); pb.write_text(''.join('EH %d %08x\n' % (k, v) for k, v in b.items()))
    return subprocess.run([sys.executable, T, str(pa), str(pb), allowed], capture_output=True, text=True).returncode
def test_declared_delete_passes(tmp_path): assert run(tmp_path, {1: 1, 2: 2}, {1: 1}, '2') == 0
def test_undeclared_delete_fails(tmp_path): assert run(tmp_path, {1: 1, 2: 2}, {1: 1}, '') == 1
def test_added_element_fails(tmp_path): assert run(tmp_path, {1: 1}, {1: 1, 2: 2}, '2') == 1
def test_changed_undeclared_fails(tmp_path): assert run(tmp_path, {1: 1}, {1: 9}, '') == 1
def test_changed_declared_passes(tmp_path): assert run(tmp_path, {1: 1}, {1: 9}, '1') == 0
