"""In-place SAVE of a no-edit Autodesk 2024 template whose file name has unicode, spaces, % & # quotes, brackets or is 200+ chars: saves, bytes identical, no stray .tmp/.part."""
import os, sys, shutil, hashlib, tempfile, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/g.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/g.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def test_odd_names():
    import pytest
    if not os.path.exists(SRC) or not save.SaveSessions().available: pytest.skip('source or savegate missing')
    for nm in ('Büro Ünï çödé 日本語 #1 %20 & x.rte', 'a' * 200 + '.rte', "it's [a] (b) {c} ~!$^;=,.rte"):
        d = os.path.join(_T, nm); shutil.copy(SRC, d); h = sha(d)
        save.save_overwrite(save.SaveSessions(), 'm', d)
        assert sha(d) == h and not [f for f in os.listdir(_T) if f.endswith(('.tmp', '.part'))], nm
        os.remove(d)
