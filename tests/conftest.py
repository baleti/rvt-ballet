import os, tempfile
# pytest runs must not write pending-edit stores into the user's real data dir
os.environ.setdefault('RVTBALLET_EDITSTORE', os.path.join(tempfile.mkdtemp(prefix='rvt-editstore-'), 'es'))

# Script-style tests (no test_ functions; the file asserts at import time) become ONE pytest item each:
# run in a subprocess, pass on rc 0, fail with the output tail otherwise. Before this, pytest imported them
# during collection and reported "0 tests" (c4x-rvtwrite2 item 19).
import re, subprocess, sys, pytest
_FN = re.compile(rb'^(async )?def test_|^class Test', re.M)


def _is_script(path):
    try: return _FN.search(open(str(path), 'rb').read()) is None
    except OSError: return False


def pytest_ignore_collect(collection_path, config):
    p = str(collection_path)
    return p.endswith('.py') and os.path.basename(p).startswith('test_') and _is_script(p) or None


class ScriptItem(pytest.Item):
    def runtest(self):
        r = subprocess.run([sys.executable, str(self.path)], capture_output=True, text=True, timeout=int(os.environ.get('RVT_SCRIPT_TEST_TIMEOUT', '900')))
        if r.returncode != 0: raise AssertionError('rc=%d\n%s' % (r.returncode, (r.stdout + r.stderr)[-2000:]))

    def reportinfo(self): return self.path, 0, 'script test ' + self.path.name


class ScriptFile(pytest.File):
    def collect(self): yield ScriptItem.from_parent(self, name=self.path.stem)


def pytest_collect_file(parent, file_path):
    if file_path.suffix == '.py' and file_path.name.startswith('test_') and _is_script(file_path): return ScriptFile.from_parent(parent, path=file_path)
