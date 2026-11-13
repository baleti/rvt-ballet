"""Library-level: save.save_as(src, src, overwrite=True) is refused (BadDest), file byte-identical; it must never bypass save_overwrite's workshared/group gates. Autodesk 2024 template."""
import os, sys, shutil, hashlib, tempfile, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def test_saveas_same_file_refused():
    import pytest
    if not os.path.exists(SRC) or not save.SaveSessions().available: pytest.skip('source or savegate missing')
    a = os.path.join(_T, 'a.rte'); shutil.copy(SRC, a); h = sha(a); ln = os.path.join(_T, 'l.rte'); os.symlink(a, ln)
    for dest in (a, ln):
        with pytest.raises(save.BadDest): save.save_as(save.SaveSessions(), 'm', a, dest, overwrite=True)
        assert sha(a) == h
    assert not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))]
