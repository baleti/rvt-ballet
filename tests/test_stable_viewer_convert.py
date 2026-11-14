"""viewer conversion (build.convert) refuses a file that changes during the conversion (conversion itself stubbed: synthetic file)"""
import os, time, tempfile, shutil, pytest
from rvtballet import build, stable


def mkfile(d):
    f = os.path.join(d, 'm.rvt'); open(f, 'wb').write(os.urandom(200000)); t = time.time() - 100; os.utime(f, (t, t)); return f


def test_convert_torn_refused(monkeypatch):
    d = tempfile.mkdtemp(); f = mkfile(d); monkeypatch.setenv(stable.ENV_QUIET, '0')
    monkeypatch.setattr(stable, 'cfb_check', lambda *a, **k: None)
    def fake(path, outdir, log=print, workers=None):
        with open(path, 'r+b') as o: o.write(b'torn')                     # Revit saving in the middle of the conversion
        return 'model built from mixed versions'
    monkeypatch.setattr(build, '_convert', fake)
    try:
        with pytest.raises(stable.FileChanged): build.convert(f, d + '/out')
    finally: shutil.rmtree(d, ignore_errors=True)


def test_convert_unchanged_passes(monkeypatch):
    d = tempfile.mkdtemp(); f = mkfile(d); monkeypatch.setenv(stable.ENV_QUIET, '0')
    monkeypatch.setattr(stable, 'cfb_check', lambda *a, **k: None)
    monkeypatch.setattr(build, '_convert', lambda *a, **k: 'ok')
    try: assert build.convert(f, d + '/out') == 'ok'
    finally: shutil.rmtree(d, ignore_errors=True)
