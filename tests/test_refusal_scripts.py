"""pytest wrapper: tests/test_save_workshared.py and test_save_group_member.py are scripts (assert at import), so pytest collected 0 tests from them.
This runs each in a subprocess and requires exit 0, an 'OK' line, and not a bare 'skip' (a skip is reported as a pytest skip, never as a pass)."""
import os, subprocess, sys, pytest
HERE = os.path.dirname(os.path.abspath(__file__))
@pytest.mark.parametrize('script', ['test_save_workshared.py', 'test_save_group_member.py', 'test_save_readonly.py', 'test_save_concurrent.py', 'test_save_conflict_samemtime.py'])
def test_refusal_script(script):
    r = subprocess.run([sys.executable, os.path.join(HERE, script)], capture_output=True, text=True, timeout=1500)
    out = r.stdout.strip()
    assert r.returncode == 0, r.stderr[-1500:]
    if out.splitlines()[-1:] == ['skip']: pytest.skip('corpus file or save sessions unavailable')
    assert 'OK' in out, out
