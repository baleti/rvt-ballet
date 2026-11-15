"""read-only guarantee: the cold query commands (also with --snapshot) leave the source byte-identical with the same mtime_ns and inode,
work on a read-only file in a read-only directory, and leave no side file next to it."""
import os, sys, stat, hashlib, shutil, subprocess, time, pytest
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
pytestmark = pytest.mark.skipif(not os.path.exists(SRC), reason='Autodesk sample not available')
ROOT = os.path.join(os.path.dirname(__file__), '..')
CMDS = [['levels'], ['info'], ['levels', '--snapshot'], ['info', '--snapshot']]


def _state(f):
    st = os.stat(f); return (st.st_size, st.st_mtime_ns, st.st_ino, hashlib.sha256(open(f, 'rb').read()).hexdigest())


@pytest.mark.parametrize('cmd', CMDS, ids=lambda c: ' '.join(c))
def test_reader_leaves_readonly_source_untouched(tmp_path, cmd):
    d = tmp_path / 'ro'; d.mkdir(); f = d / 'a.rvt'; shutil.copyfile(SRC, f)
    t = time.time() - 100; os.utime(f, (t, t)); os.chmod(f, 0o444); os.chmod(d, 0o555)
    try:
        before = _state(str(f)); names = sorted(os.listdir(d))
        p = subprocess.run([sys.executable, '-m', 'rvtballet', cmd[0], str(f), '--quiet-secs', '0'] + cmd[1:], cwd=ROOT, capture_output=True, text=True, timeout=300)
        assert p.returncode == 0, p.stderr[-300:]
        assert _state(str(f)) == before and sorted(os.listdir(d)) == names
    finally: os.chmod(d, 0o755)
