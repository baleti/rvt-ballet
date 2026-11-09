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


def _timeout(path):
    # a slow-by-design test declares '# RVT_TEST_TIMEOUT=<seconds>' in its first 2 KB (corpus loops)
    m = re.search(rb'RVT_TEST_TIMEOUT=(\d+)', open(str(path), 'rb').read(2048))
    return int(m.group(1)) if m else int(os.environ.get('RVT_SCRIPT_TEST_TIMEOUT', '900'))


class ScriptItem(pytest.Item):
    def runtest(self):
        r = subprocess.run([sys.executable, str(self.path)], capture_output=True, text=True, timeout=_timeout(self.path))
        if r.returncode != 0: raise AssertionError('rc=%d\n%s' % (r.returncode, (r.stdout + r.stderr)[-2000:]))

    def reportinfo(self): return self.path, 0, 'script test ' + self.path.name


class ScriptFile(pytest.File):
    def collect(self): yield ScriptItem.from_parent(self, name=self.path.stem)


def pytest_pycollect_makemodule(module_path, parent):
    if module_path.name.startswith('test_') and _is_script(module_path): return ScriptFile.from_parent(parent, path=module_path)
